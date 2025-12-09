# quiz/admin_enhanced.py - Enhanced admin configuration
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    QuestionRating, TimedQuizSession, UserPreferences,
    PerformanceMetrics, QuestionCache, Leaderboard
)


@admin.register(QuestionRating)
class QuestionRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_preview', 'rating_stars', 'flags', 'created_at']
    list_filter = ['rating', 'is_too_easy', 'is_too_hard', 'is_unclear', 'created_at']
    search_fields = ['user__username', 'question__question_text', 'feedback']
    readonly_fields = ['created_at']
    
    def question_preview(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_preview.short_description = 'Question'
    
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        return format_html(f'<span style="color: #F59E0B;">{stars}</span>')
    rating_stars.short_description = 'Rating'
    
    def flags(self, obj):
        flags = []
        if obj.is_too_easy:
            flags.append('<span style="color: green;">Easy</span>')
        if obj.is_too_hard:
            flags.append('<span style="color: red;">Hard</span>')
        if obj.is_unclear:
            flags.append('<span style="color: orange;">Unclear</span>')
        return format_html(' | '.join(flags)) if flags else '-'
    flags.short_description = 'Flags'


@admin.register(TimedQuizSession)
class TimedQuizSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'duration_minutes', 'questions_count', 'status_badge', 'score', 'started_at', 'time_taken_display']
    list_filter = ['status', 'duration_minutes', 'started_at']
    search_fields = ['user__username']
    readonly_fields = ['started_at', 'completed_at']
    
    def status_badge(self, obj):
        colors = {
            'active': '#10B981',
            'completed': '#7C3AED',
            'expired': '#EF4444'
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            f'<span style="background: {color}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{obj.status.upper()}</span>'
        )
    status_badge.short_description = 'Status'
    
    def time_taken_display(self, obj):
        if obj.time_taken_seconds:
            minutes = obj.time_taken_seconds // 60
            seconds = obj.time_taken_seconds % 60
            return f"{minutes}m {seconds}s"
        return '-'
    time_taken_display.short_description = 'Time Taken'


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme_badge', 'preferred_difficulty', 'features_enabled', 'updated_at']
    list_filter = ['theme', 'preferred_difficulty', 'enable_sound', 'enable_animations']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Appearance', {
            'fields': ('theme',)
        }),
        ('Quiz Settings', {
            'fields': ('preferred_difficulty', 'questions_per_session', 'auto_next_question', 'show_explanations')
        }),
        ('Features', {
            'fields': ('enable_sound', 'enable_animations', 'enable_keyboard_shortcuts')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def theme_badge(self, obj):
        colors = {
            'light': '#F3F4F6',
            'dark': '#1F2937',
            'auto': '#7C3AED'
        }
        bg_color = colors.get(obj.theme, '#6B7280')
        text_color = 'black' if obj.theme == 'light' else 'white'
        return format_html(
            f'<span style="background: {bg_color}; color: {text_color}; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{obj.theme.upper()}</span>'
        )
    theme_badge.short_description = 'Theme'
    
    def features_enabled(self, obj):
        features = []
        if obj.enable_sound:
            features.append('🔊')
        if obj.enable_animations:
            features.append('✨')
        if obj.enable_keyboard_shortcuts:
            features.append('⌨️')
        return ' '.join(features) if features else '-'
    features_enabled.short_description = 'Features'


@admin.register(PerformanceMetrics)
class PerformanceMetricsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'questions_attempted', 'accuracy_display', 'streak_count', 'study_time_display']
    list_filter = ['date', 'streak_count']
    search_fields = ['user__username']
    readonly_fields = ['date', 'accuracy_percentage']
    
    def accuracy_display(self, obj):
        accuracy = obj.accuracy_percentage
        color = '#10B981' if accuracy >= 80 else '#F59E0B' if accuracy >= 60 else '#EF4444'
        return format_html(
            f'<span style="color: {color}; font-weight: bold;">{accuracy}%</span>'
        )
    accuracy_display.short_description = 'Accuracy'
    
    def study_time_display(self, obj):
        hours = obj.study_time_minutes // 60
        minutes = obj.study_time_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    study_time_display.short_description = 'Study Time'


@admin.register(QuestionCache)
class QuestionCacheAdmin(admin.ModelAdmin):
    list_display = ['cache_key', 'question_preview', 'hit_count', 'last_accessed', 'created_at']
    list_filter = ['created_at', 'last_accessed']
    search_fields = ['cache_key', 'question__question_text']
    readonly_fields = ['created_at', 'last_accessed']
    ordering = ['-hit_count']
    
    def question_preview(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_preview.short_description = 'Question'


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['rank_badge', 'user', 'period', 'score', 'questions_answered', 'accuracy_display', 'updated_at']
    list_filter = ['period', 'period_start']
    search_fields = ['user__username']
    readonly_fields = ['updated_at']
    ordering = ['period', 'rank']
    
    def rank_badge(self, obj):
        if obj.rank == 1:
            return format_html('<span style="font-size: 20px;">🥇</span> #{}'.format(obj.rank))
        elif obj.rank == 2:
            return format_html('<span style="font-size: 20px;">🥈</span> #{}'.format(obj.rank))
        elif obj.rank == 3:
            return format_html('<span style="font-size: 20px;">🥉</span> #{}'.format(obj.rank))
        else:
            return f'#{obj.rank}'
    rank_badge.short_description = 'Rank'
    
    def accuracy_display(self, obj):
        color = '#10B981' if obj.accuracy >= 80 else '#F59E0B' if obj.accuracy >= 60 else '#EF4444'
        return format_html(
            f'<span style="color: {color}; font-weight: bold;">{obj.accuracy:.2f}%</span>'
        )
    accuracy_display.short_description = 'Accuracy'
