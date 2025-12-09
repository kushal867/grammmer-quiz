# quiz/views_enhanced.py - New enhanced feature endpoints
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Avg, Count, Q, F
from datetime import datetime, timedelta
import json
import logging

from .models import (
    Question, UserAnswer, QuizAttempt, QuestionRating,
    TimedQuizSession, UserPreferences, PerformanceMetrics,
    QuestionCache, Leaderboard, UserProfile
)

logger = logging.getLogger(__name__)


# ==================== QUESTION RATING ====================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_rate_question(request):
    """Rate a question"""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        rating = data.get('rating')
        feedback = data.get('feedback', '')
        is_too_easy = data.get('is_too_easy', False)
        is_too_hard = data.get('is_too_hard', False)
        is_unclear = data.get('is_unclear', False)
        
        if not question_id or not rating:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        question = Question.objects.get(id=question_id)
        
        # Create or update rating
        rating_obj, created = QuestionRating.objects.update_or_create(
            user=request.user,
            question=question,
            defaults={
                'rating': rating,
                'feedback': feedback,
                'is_too_easy': is_too_easy,
                'is_too_hard': is_too_hard,
                'is_unclear': is_unclear,
            }
        )
        
        # Calculate average rating
        avg_rating = QuestionRating.objects.filter(question=question).aggregate(
            Avg('rating')
        )['rating__avg']
        
        return JsonResponse({
            'success': True,
            'message': 'Rating submitted successfully',
            'average_rating': round(avg_rating, 2) if avg_rating else 0,
            'total_ratings': QuestionRating.objects.filter(question=question).count()
        })
        
    except Question.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    except Exception as e:
        logger.error(f"Error rating question: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_get_question_ratings(request, question_id):
    """Get ratings for a specific question"""
    try:
        question = Question.objects.get(id=question_id)
        ratings = QuestionRating.objects.filter(question=question)
        
        avg_rating = ratings.aggregate(Avg('rating'))['rating__avg']
        
        rating_distribution = {
            '5': ratings.filter(rating=5).count(),
            '4': ratings.filter(rating=4).count(),
            '3': ratings.filter(rating=3).count(),
            '2': ratings.filter(rating=2).count(),
            '1': ratings.filter(rating=1).count(),
        }
        
        return JsonResponse({
            'success': True,
            'average_rating': round(avg_rating, 2) if avg_rating else 0,
            'total_ratings': ratings.count(),
            'distribution': rating_distribution,
            'feedback_stats': {
                'too_easy': ratings.filter(is_too_easy=True).count(),
                'too_hard': ratings.filter(is_too_hard=True).count(),
                'unclear': ratings.filter(is_unclear=True).count(),
            }
        })
        
    except Question.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting question ratings: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== TIMED QUIZ ====================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_start_timed_quiz(request):
    """Start a new timed quiz session"""
    try:
        data = json.loads(request.body)
        duration_minutes = data.get('duration', 30)
        questions_count = data.get('questions_count', 20)
        
        # Check if user has an active session
        active_session = TimedQuizSession.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if active_session and not active_session.is_expired:
            return JsonResponse({
                'error': 'You already have an active timed quiz session',
                'session_id': active_session.id
            }, status=400)
        
        # Create new session
        session = TimedQuizSession.objects.create(
            user=request.user,
            duration_minutes=duration_minutes,
            questions_count=questions_count
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'duration_minutes': duration_minutes,
            'questions_count': questions_count,
            'started_at': session.started_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error starting timed quiz: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_submit_timed_quiz(request):
    """Submit a timed quiz session"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        score = data.get('score', 0)
        
        session = TimedQuizSession.objects.get(id=session_id, user=request.user)
        
        if session.status == 'completed':
            return JsonResponse({'error': 'Session already completed'}, status=400)
        
        # Calculate time taken
        time_taken = (timezone.now() - session.started_at).total_seconds()
        
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.score = score
        session.time_taken_seconds = int(time_taken)
        session.save()
        
        return JsonResponse({
            'success': True,
            'score': score,
            'time_taken_seconds': int(time_taken),
            'time_taken_formatted': f"{int(time_taken // 60)}m {int(time_taken % 60)}s"
        })
        
    except TimedQuizSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error submitting timed quiz: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def api_timed_quiz_status(request):
    """Get status of active timed quiz session"""
    try:
        session = TimedQuizSession.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not session:
            return JsonResponse({'active': False})
        
        if session.is_expired:
            session.status = 'expired'
            session.save()
            return JsonResponse({'active': False, 'expired': True})
        
        elapsed = (timezone.now() - session.started_at).total_seconds()
        remaining = (session.duration_minutes * 60) - elapsed
        
        return JsonResponse({
            'active': True,
            'session_id': session.id,
            'elapsed_seconds': int(elapsed),
            'remaining_seconds': int(remaining),
            'duration_minutes': session.duration_minutes,
            'questions_count': session.questions_count
        })
        
    except Exception as e:
        logger.error(f"Error getting timed quiz status: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def timed_quiz_page(request):
    """Timed quiz page"""
    return render(request, 'timed_quiz.html')


# ==================== PERFORMANCE ANALYTICS ====================

@require_http_methods(["GET"])
@login_required
def api_performance_analytics(request):
    """Get detailed performance analytics"""
    try:
        # Get user profile
        profile = request.user.profile
        
        # Get recent performance metrics
        recent_metrics = PerformanceMetrics.objects.filter(
            user=request.user
        ).order_by('-date')[:30]
        
        # Calculate overall stats
        total_attempts = QuizAttempt.objects.filter(user=request.user).count()
        total_answers = UserAnswer.objects.filter(user=request.user).count()
        correct_answers = UserAnswer.objects.filter(user=request.user, is_correct=True).count()
        
        # Domain breakdown
        domain_stats = {}
        for metric in recent_metrics:
            for domain, stats in metric.domains_covered.items():
                if domain not in domain_stats:
                    domain_stats[domain] = {'correct': 0, 'total': 0}
                domain_stats[domain]['correct'] += stats.get('correct', 0)
                domain_stats[domain]['total'] += stats.get('total', 0)
        
        # Calculate accuracy per domain
        for domain in domain_stats:
            total = domain_stats[domain]['total']
            if total > 0:
                domain_stats[domain]['accuracy'] = round(
                    (domain_stats[domain]['correct'] / total) * 100, 2
                )
            else:
                domain_stats[domain]['accuracy'] = 0
        
        return JsonResponse({
            'success': True,
            'overall': {
                'total_questions': profile.total_questions_attempted,
                'correct_answers': profile.correct_answers,
                'accuracy': profile.accuracy,
                'streak_days': profile.streak_days,
                'total_attempts': total_attempts,
            },
            'domain_breakdown': domain_stats,
            'recent_activity': [
                {
                    'date': metric.date.isoformat(),
                    'questions': metric.questions_attempted,
                    'correct': metric.questions_correct,
                    'accuracy': metric.accuracy_percentage,
                    'study_time': metric.study_time_minutes
                }
                for metric in recent_metrics
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def api_performance_trends(request):
    """Get performance trends over time"""
    try:
        days = int(request.GET.get('days', 30))
        
        metrics = PerformanceMetrics.objects.filter(
            user=request.user,
            date__gte=timezone.now().date() - timedelta(days=days)
        ).order_by('date')
        
        trends = {
            'dates': [],
            'accuracy': [],
            'questions_attempted': [],
            'study_time': [],
            'streak': []
        }
        
        for metric in metrics:
            trends['dates'].append(metric.date.isoformat())
            trends['accuracy'].append(metric.accuracy_percentage)
            trends['questions_attempted'].append(metric.questions_attempted)
            trends['study_time'].append(metric.study_time_minutes)
            trends['streak'].append(metric.streak_count)
        
        return JsonResponse({
            'success': True,
            'trends': trends,
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def api_domain_breakdown(request):
    """Get detailed domain-wise performance breakdown"""
    try:
        answers = UserAnswer.objects.filter(user=request.user).select_related('question')
        
        domain_breakdown = {}
        
        for answer in answers:
            domain = answer.question.domain
            if domain not in domain_breakdown:
                domain_breakdown[domain] = {
                    'total': 0,
                    'correct': 0,
                    'topics': {}
                }
            
            domain_breakdown[domain]['total'] += 1
            if answer.is_correct:
                domain_breakdown[domain]['correct'] += 1
            
            # Topic breakdown
            topic = answer.question.topic
            if topic not in domain_breakdown[domain]['topics']:
                domain_breakdown[domain]['topics'][topic] = {'total': 0, 'correct': 0}
            
            domain_breakdown[domain]['topics'][topic]['total'] += 1
            if answer.is_correct:
                domain_breakdown[domain]['topics'][topic]['correct'] += 1
        
        # Calculate accuracies
        for domain in domain_breakdown:
            total = domain_breakdown[domain]['total']
            correct = domain_breakdown[domain]['correct']
            domain_breakdown[domain]['accuracy'] = round((correct / total) * 100, 2) if total > 0 else 0
            
            for topic in domain_breakdown[domain]['topics']:
                topic_total = domain_breakdown[domain]['topics'][topic]['total']
                topic_correct = domain_breakdown[domain]['topics'][topic]['correct']
                domain_breakdown[domain]['topics'][topic]['accuracy'] = round(
                    (topic_correct / topic_total) * 100, 2
                ) if topic_total > 0 else 0
        
        return JsonResponse({
            'success': True,
            'domain_breakdown': domain_breakdown
        })
        
    except Exception as e:
        logger.error(f"Error getting domain breakdown: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== LEADERBOARD ====================

@require_http_methods(["GET"])
def api_leaderboard(request):
    """Get leaderboard for all periods"""
    try:
        period = request.GET.get('period', 'weekly')
        limit = int(request.GET.get('limit', 50))
        
        today = timezone.now().date()
        
        if period == 'daily':
            period_start = today
        elif period == 'weekly':
            period_start = today - timedelta(days=today.weekday())
        elif period == 'monthly':
            period_start = today.replace(day=1)
        else:  # all_time
            period_start = None
        
        if period_start:
            entries = Leaderboard.objects.filter(
                period=period,
                period_start=period_start
            ).select_related('user').order_by('rank')[:limit]
        else:
            entries = Leaderboard.objects.filter(
                period='all_time'
            ).select_related('user').order_by('rank')[:limit]
        
        leaderboard_data = [
            {
                'rank': entry.rank,
                'username': entry.user.username,
                'score': entry.score,
                'questions_answered': entry.questions_answered,
                'accuracy': round(entry.accuracy, 2),
                'is_current_user': entry.user == request.user if request.user.is_authenticated else False
            }
            for entry in entries
        ]
        
        # Get current user's rank if authenticated
        user_rank = None
        if request.user.is_authenticated:
            user_entry = Leaderboard.objects.filter(
                user=request.user,
                period=period
            ).first()
            if user_entry:
                user_rank = user_entry.rank
        
        return JsonResponse({
            'success': True,
            'period': period,
            'leaderboard': leaderboard_data,
            'user_rank': user_rank,
            'total_entries': Leaderboard.objects.filter(period=period).count()
        })
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_leaderboard_by_period(request, period):
    """Get leaderboard for specific period"""
    request.GET = request.GET.copy()
    request.GET['period'] = period
    return api_leaderboard(request)


@login_required
def leaderboard_page(request):
    """Leaderboard page"""
    return render(request, 'leaderboard.html')


# ==================== USER PREFERENCES ====================

@require_http_methods(["GET"])
@login_required
def api_get_preferences(request):
    """Get user preferences"""
    try:
        preferences, created = UserPreferences.objects.get_or_create(user=request.user)
        
        return JsonResponse({
            'success': True,
            'preferences': {
                'theme': preferences.theme,
                'preferred_difficulty': preferences.preferred_difficulty,
                'enable_sound': preferences.enable_sound,
                'enable_animations': preferences.enable_animations,
                'show_explanations': preferences.show_explanations,
                'auto_next_question': preferences.auto_next_question,
                'questions_per_session': preferences.questions_per_session,
                'enable_keyboard_shortcuts': preferences.enable_keyboard_shortcuts,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_update_preferences(request):
    """Update user preferences"""
    try:
        data = json.loads(request.body)
        preferences, created = UserPreferences.objects.get_or_create(user=request.user)
        
        # Update fields
        for field in ['theme', 'preferred_difficulty', 'enable_sound', 'enable_animations',
                      'show_explanations', 'auto_next_question', 'questions_per_session',
                      'enable_keyboard_shortcuts']:
            if field in data:
                setattr(preferences, field, data[field])
        
        preferences.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Preferences updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== DASHBOARD ====================

@login_required
def dashboard_page(request):
    """User dashboard with comprehensive statistics"""
    try:
        profile = request.user.profile
        
        # Get recent activity
        recent_attempts = QuizAttempt.objects.filter(
            user=request.user
        ).order_by('-started_at')[:10]
        
        # Get performance metrics
        recent_metrics = PerformanceMetrics.objects.filter(
            user=request.user
        ).order_by('-date')[:7]
        
        # Get achievements
        achievements = request.user.achievements.select_related('achievement').order_by('-unlocked_at')[:5]
        
        # Get leaderboard position
        leaderboard_entry = Leaderboard.objects.filter(
            user=request.user,
            period='weekly'
        ).first()
        
        context = {
            'profile': profile,
            'recent_attempts': recent_attempts,
            'recent_metrics': recent_metrics,
            'achievements': achievements,
            'leaderboard_rank': leaderboard_entry.rank if leaderboard_entry else None,
        }
        
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render(request, 'dashboard.html', {'error': str(e)})
