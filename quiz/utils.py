# quiz/utils.py - Helper functions for advanced features
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import random
from .models import (
    Question, DailyChallenge, UserProfile, UserAnswer,
    BookmarkedQuestion, QuizAttempt, Achievement, UserAchievement
)


def get_or_create_daily_challenge(date=None):
    """Get or create daily challenge for a specific date"""
    if date is None:
        date = timezone.now().date()
    
    challenge, created = DailyChallenge.objects.get_or_create(date=date)
    
    if created or challenge.questions.count() == 0:
        # Generate 10 questions for the daily challenge
        # Mix of difficulties and domains
        questions = []
        
        # 3 easy, 4 medium, 3 hard
        difficulties = ['सजिलो'] * 3 + ['मध्यम'] * 4 + ['कठिन'] * 3
        
        for difficulty in difficulties:
            # Get approved questions
            available_questions = Question.objects.filter(
                is_approved=True,
                difficulty=difficulty
            ).exclude(
                id__in=[q.id for q in questions]
            )
            
            if available_questions.exists():
                question = random.choice(available_questions)
                questions.append(question)
        
        if questions:
            challenge.questions.set(questions)
    
    return challenge


def check_and_update_streak(user):
    """Check and update user's streak"""
    profile = user.profile
    today = timezone.now().date()
    
    if profile.last_daily_challenge:
        days_diff = (today - profile.last_daily_challenge).days
        
        if days_diff == 1:
            # Consecutive day
            profile.streak_days += 1
        elif days_diff > 1:
            # Streak broken
            profile.streak_days = 1
        # If days_diff == 0, same day, don't change streak
    else:
        # First time
        profile.streak_days = 1
    
    profile.last_daily_challenge = today
    profile.save()
    
    # Check for streak achievements
    check_achievements(user)


def check_achievements(user):
    """Check and unlock achievements for user"""
    profile = user.profile
    unlocked = []
    
    # Get all achievements
    achievements = Achievement.objects.all()
    
    for achievement in achievements:
        # Skip if already unlocked
        if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            continue
        
        should_unlock = False
        
        if achievement.achievement_type == 'streak':
            should_unlock = profile.streak_days >= achievement.requirement
        
        elif achievement.achievement_type == 'accuracy':
            should_unlock = profile.accuracy >= achievement.requirement
        
        elif achievement.achievement_type == 'questions':
            should_unlock = profile.total_questions_attempted >= achievement.requirement
        
        elif achievement.achievement_type == 'daily':
            daily_count = user.daily_completions.count()
            should_unlock = daily_count >= achievement.requirement
        
        if should_unlock:
            UserAchievement.objects.create(user=user, achievement=achievement)
            unlocked.append(achievement)
    
    return unlocked


def save_question_to_db(question_data, difficulty):
    """Save AI-generated question to database"""
    question = Question.objects.create(
        domain=question_data.get('domain', 'सामान्य ज्ञान'),
        topic=question_data.get('topic', 'सामान्य'),
        difficulty=difficulty,
        question_text=question_data['question'],
        options=question_data['options'],
        correct_answer=question_data['correct_letter'],
        explanation=question_data.get('explanation', ''),
        is_approved=True,  # Auto-approve for now
        is_reviewed=False
    )
    return question


def save_user_answer(user, question, selected_answer, is_correct, quiz_attempt=None):
    """Save user's answer to database"""
    answer = UserAnswer.objects.create(
        user=user,
        question=question,
        quiz_attempt=quiz_attempt,
        selected_answer=selected_answer,
        is_correct=is_correct
    )
    
    # Update user profile
    profile = user.profile
    profile.total_questions_attempted += 1
    if is_correct:
        profile.correct_answers += 1
    profile.save()
    
    # Check for achievements
    check_achievements(user)
    
    return answer


def search_questions(query, domain=None, difficulty=None, user=None):
    """Search questions with filters"""
    questions = Question.objects.filter(is_approved=True)
    
    if query:
        questions = questions.filter(
            Q(question_text__icontains=query) |
            Q(topic__icontains=query) |
            Q(domain__icontains=query)
        )
    
    if domain:
        questions = questions.filter(domain=domain)
    
    if difficulty:
        questions = questions.filter(difficulty=difficulty)
    
    return questions.distinct()


def get_user_statistics(user):
    """Get comprehensive user statistics"""
    profile = user.profile
    
    # Domain-wise performance
    domain_stats = UserAnswer.objects.filter(user=user).values(
        'question__domain'
    ).annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    )
    
    # Recent activity
    recent_answers = UserAnswer.objects.filter(user=user).order_by('-answered_at')[:10]
    
    # Quiz attempts
    quiz_attempts = QuizAttempt.objects.filter(user=user).order_by('-started_at')[:5]
    
    # Achievements
    achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
    
    return {
        'profile': profile,
        'domain_stats': list(domain_stats),
        'recent_answers': recent_answers,
        'quiz_attempts': quiz_attempts,
        'achievements': achievements,
        'total_bookmarks': BookmarkedQuestion.objects.filter(user=user).count()
    }
