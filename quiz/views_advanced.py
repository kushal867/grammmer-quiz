# quiz/views_advanced.py - Advanced feature endpoints
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv
import logging

from .models import (
    Question, BookmarkedQuestion, DailyChallenge, DailyChallengeCompletion,
    QuizAttempt, UserAnswer, Achievement, UserAchievement
)
from .utils import (
    get_or_create_daily_challenge, check_and_update_streak,
    save_user_answer, search_questions, get_user_statistics
)

logger = logging.getLogger(__name__)


# ... existing code ...

@login_required
def dashboard_page(request):
    """User dashboard page"""
    stats = get_user_statistics(request.user)
    
    # Get leaderboard rank (approximate)
    from django.db.models import Sum
    leaderboard = UserAnswer.objects.values('user').annotate(
        total_score=Count('id', filter=Q(is_correct=True))
    ).order_by('-total_score')
    
    rank = 0
    for i, entry in enumerate(leaderboard):
        if entry['user'] == request.user.id:
            rank = i + 1
            break
            
    recent_attempts = QuizAttempt.objects.filter(user=request.user).order_by('-started_at')[:5]
    
    return render(request, 'dashboard.html', {
        **stats,
        'leaderboard_rank': rank,
        'recent_attempts': recent_attempts
    })


@login_required
def leaderboard_page(request):
    """Leaderboard page"""
    return render(request, 'leaderboard.html')


@require_http_methods(["GET"])
def api_leaderboard(request, period='weekly'):
    """API for leaderboard data"""
    from django.contrib.auth.models import User
    
    # Filter by period
    since = timezone.now()
    if period == 'weekly':
        since -= timedelta(days=7)
    elif period == 'monthly':
        since -= timedelta(days=30)
    else:
        since = datetime(2000, 1, 1) # All time
        
    leaderboard_data = UserAnswer.objects.filter(
        answered_at__gte=since
    ).values('user__username', 'user__id').annotate(
        score=Count('id', filter=Q(is_correct=True)),
        total=Count('id')
    ).order_by('-score')[:50]
    
    results = []
    for i, entry in enumerate(leaderboard_data):
        results.append({
            'rank': i + 1,
            'username': entry['user__username'],
            'score': entry['score'],
            'questions_answered': entry['total'],
            'accuracy': round((entry['score'] / entry['total'] * 100), 1) if entry['total'] > 0 else 0,
            'is_current_user': entry['user__id'] == request.user.id if request.user.is_authenticated else False
        })
        
    return JsonResponse({'success': True, 'leaderboard': results})


# ==================== DAILY CHALLENGE ====================

@login_required
@require_http_methods(["GET"])
def api_daily_challenge(request):
    """Get today's daily challenge"""
    try:
        challenge = get_or_create_daily_challenge()
        questions_data = []
        
        for question in challenge.questions.all():
            questions_data.append({
                'id': question.id,
                'question': question.question_text,
                'options': question.options,
                'correct_answer': question.correct_answer,
                'domain': question.domain,
                'topic': question.topic,
                'difficulty': question.difficulty
            })
        
        # Check if user already completed today's challenge
        completed = DailyChallengeCompletion.objects.filter(
            user=request.user,
            challenge=challenge
        ).exists()
        
        return JsonResponse({
            'success': True,
            'date': challenge.date.isoformat(),
            'questions': questions_data,
            'total_questions': len(questions_data),
            'completed': completed,
            'streak': request.user.profile.streak_days
        })
    
    except Exception as e:
        logger.error(f"Error in api_daily_challenge: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def daily_challenge_page(request):
    """Daily challenge page"""
    return render(request, 'daily_challenge.html')


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_complete_daily_challenge(request):
    """Mark daily challenge as completed"""
    try:
        data = json.loads(request.body)
        score = data.get('score', 0)
        total = data.get('total', 10)
        
        challenge = get_or_create_daily_challenge()
        
        # Create or update completion
        completion, created = DailyChallengeCompletion.objects.get_or_create(
            user=request.user,
            challenge=challenge,
            defaults={'score': score, 'total_questions': total}
        )
        
        if not created:
            # Update if better score
            if score > completion.score:
                completion.score = score
                completion.save()
        
        # Update streak
        check_and_update_streak(request.user)
        
        return JsonResponse({
            'success': True,
            'score': score,
            'total': total,
            'streak': request.user.profile.streak_days,
            'message': f'बधाई छ! तपाईंको स्ट्रिक: {request.user.profile.streak_days} दिन'
        })
    
    except Exception as e:
        logger.error(f"Error in api_complete_daily_challenge: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== BOOKMARK SYSTEM ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_bookmark_question(request):
    """Bookmark a question"""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        notes = data.get('notes', '')
        tags = data.get('tags', '')
        
        if not question_id:
            return JsonResponse({'error': 'Question ID required'}, status=400)
        
        question = Question.objects.get(id=question_id)
        
        bookmark, created = BookmarkedQuestion.objects.get_or_create(
            user=request.user,
            question=question,
            defaults={'notes': notes, 'tags': tags}
        )
        
        if not created:
            # Update existing bookmark
            bookmark.notes = notes
            bookmark.tags = tags
            bookmark.save()
        
        return JsonResponse({
            'success': True,
            'bookmarked': True,
            'message': 'प्रश्न बुकमार्क गरियो',
            'bookmark_id': bookmark.id
        })
    
    except Question.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in api_bookmark_question: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_remove_bookmark(request):
    """Remove a bookmark"""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        
        if not question_id:
            return JsonResponse({'error': 'Question ID required'}, status=400)
        
        BookmarkedQuestion.objects.filter(
            user=request.user,
            question_id=question_id
        ).delete()
        
        return JsonResponse({
            'success': True,
            'message': 'बुकमार्क हटाइयो'
        })
    
    except Exception as e:
        logger.error(f"Error in api_remove_bookmark: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_bookmarks(request):
    """Get user's bookmarked questions"""
    try:
        bookmarks = BookmarkedQuestion.objects.filter(
            user=request.user
        ).select_related('question').order_by('-created_at')
        
        bookmarks_data = []
        for bookmark in bookmarks:
            bookmarks_data.append({
                'id': bookmark.id,
                'question_id': bookmark.question.id,
                'question': bookmark.question.question_text,
                'options': bookmark.question.options,
                'correct_answer': bookmark.question.correct_answer,
                'domain': bookmark.question.domain,
                'topic': bookmark.question.topic,
                'difficulty': bookmark.question.difficulty,
                'notes': bookmark.notes,
                'tags': bookmark.tags,
                'created_at': bookmark.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'bookmarks': bookmarks_data,
            'total': len(bookmarks_data)
        })
    
    except Exception as e:
        logger.error(f"Error in api_get_bookmarks: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== SEARCH ====================

@login_required
@require_http_methods(["GET"])
def api_search_questions(request):
    """Search questions with filters"""
    try:
        query = request.GET.get('q', '')
        domain = request.GET.get('domain', '')
        difficulty = request.GET.get('difficulty', '')
        bookmarks_only = request.GET.get('bookmarks_only', 'false').lower() == 'true'
        
        if bookmarks_only:
            # Search only in bookmarked questions
            bookmark_ids = BookmarkedQuestion.objects.filter(
                user=request.user
            ).values_list('question_id', flat=True)
            questions = Question.objects.filter(id__in=bookmark_ids)
        else:
            questions = search_questions(query, domain, difficulty, request.user)
        
        # Limit results
        questions = questions[:50]
        
        results = []
        for question in questions:
            results.append({
                'id': question.id,
                'question': question.question_text,
                'domain': question.domain,
                'topic': question.topic,
                'difficulty': question.difficulty,
                'is_bookmarked': BookmarkedQuestion.objects.filter(
                    user=request.user,
                    question=question
                ).exists()
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total': len(results),
            'query': query
        })
    
    except Exception as e:
        logger.error(f"Error in api_search_questions: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== USER PROFILE ====================

@login_required
def user_profile(request):
    """User profile page with statistics"""
    stats = get_user_statistics(request.user)
    return render(request, 'profile.html', stats)


@login_required
@require_http_methods(["GET"])
def api_user_stats(request):
    """Get user statistics as JSON"""
    try:
        stats = get_user_statistics(request.user)
        
        # Convert to JSON-serializable format
        return JsonResponse({
            'success': True,
            'profile': {
                'username': request.user.username,
                'total_questions': stats['profile'].total_questions_attempted,
                'correct_answers': stats['profile'].correct_answers,
                'accuracy': stats['profile'].accuracy,
                'streak_days': stats['profile'].streak_days,
                'last_activity': stats['profile'].last_activity.isoformat()
            },
            'domain_stats': stats['domain_stats'],
            'total_bookmarks': stats['total_bookmarks'],
            'achievements_count': stats['achievements'].count()
        })
    
    except Exception as e:
        logger.error(f"Error in api_user_stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== EXPORT ====================

@login_required
def export_csv(request):
    """Export user's quiz history as CSV"""
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="quiz_history_{request.user.username}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Question', 'Domain', 'Topic', 'Difficulty', 'Your Answer', 'Correct Answer', 'Result'])
        
        answers = UserAnswer.objects.filter(user=request.user).select_related('question').order_by('-answered_at')
        
        for answer in answers:
            writer.writerow([
                answer.answered_at.strftime('%Y-%m-%d %H:%M'),
                answer.question.question_text[:100],
                answer.question.domain,
                answer.question.topic,
                answer.question.difficulty,
                answer.selected_answer,
                answer.question.correct_answer,
                'सही' if answer.is_correct else 'गलत'
            ])
        
        return response
    
    except Exception as e:
        logger.error(f"Error in export_csv: {e}")
        return HttpResponse(f'Error: {str(e)}', status=500)


@login_required
def export_pdf(request):
    """Export user statistics as PDF"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#6b46c1'),
            spaceAfter=30,
            alignment=1  # Center
        )
        elements.append(Paragraph(f'Quiz Report - {request.user.username}', title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Get statistics
        stats = get_user_statistics(request.user)
        profile = stats['profile']
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Questions Attempted', str(profile.total_questions_attempted)],
            ['Correct Answers', str(profile.correct_answers)],
            ['Accuracy', f'{profile.accuracy}%'],
            ['Current Streak', f'{profile.streak_days} days'],
            ['Total Bookmarks', str(stats['total_bookmarks'])],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6b46c1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Domain-wise performance
        elements.append(Paragraph('Domain-wise Performance', styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        domain_data = [['Domain', 'Total', 'Correct', 'Accuracy']]
        for domain_stat in stats['domain_stats']:
            domain = domain_stat['question__domain']
            total = domain_stat['total']
            correct = domain_stat['correct']
            accuracy = round((correct / total * 100), 2) if total > 0 else 0
            domain_data.append([domain, str(total), str(correct), f'{accuracy}%'])
        
        if len(domain_data) > 1:
            domain_table = Table(domain_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            domain_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#a78bfa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(domain_table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="quiz_report_{request.user.username}.pdf"'
        return response
    
    except ImportError:
        return HttpResponse('PDF export requires reportlab library. Install with: pip install reportlab', status=500)
    except Exception as e:
        logger.error(f"Error in export_pdf: {e}")
        return HttpResponse(f'Error: {str(e)}', status=500)


# ==================== BOOKMARKS PAGE ====================

@login_required
def bookmarks_page(request):
    """Bookmarks page"""
    return render(request, 'bookmarks.html')
