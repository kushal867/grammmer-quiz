from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, Question, QuizAttempt, UserAnswer,
    BookmarkedQuestion, DailyChallenge, DailyChallengeCompletion,
    Achievement, UserAchievement
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_questions_attempted', 'correct_answers', 'accuracy', 'streak_days', 'last_activity']
    list_filter = ['streak_days', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'last_activity']
    
    def accuracy(self, obj):
        return f"{obj.accuracy}%"
    accuracy.short_description = 'Accuracy'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'domain', 'topic', 'difficulty', 'is_approved', 'is_reviewed', 'times_used', 'created_at']
    list_filter = ['domain', 'difficulty', 'is_approved', 'is_reviewed', 'created_at']
    search_fields = ['question_text', 'topic', 'domain']
    readonly_fields = ['created_at', 'times_used']
    actions = ['approve_questions', 'reject_questions', 'mark_as_reviewed']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('domain', 'topic', 'difficulty', 'question_text')
        }),
        ('Answer Options', {
            'fields': ('options', 'correct_answer', 'explanation')
        }),
        ('Review Status', {
            'fields': ('is_approved', 'is_reviewed', 'times_used', 'created_at')
        }),
    )
    
    def question_preview(self, obj):
        return obj.question_text[:80] + '...' if len(obj.question_text) > 80 else obj.question_text
    question_preview.short_description = 'Question'
    
    def approve_questions(self, request, queryset):
        updated = queryset.update(is_approved=True, is_reviewed=True)
        self.message_user(request, f'{updated} questions approved successfully.')
    approve_questions.short_description = 'Approve selected questions'
    
    def reject_questions(self, request, queryset):
        updated = queryset.update(is_approved=False, is_reviewed=True)
        self.message_user(request, f'{updated} questions rejected.')
    reject_questions.short_description = 'Reject selected questions'
    
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f'{updated} questions marked as reviewed.')
    mark_as_reviewed.short_description = 'Mark as reviewed'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'started_at', 'completed_at', 'total_questions', 'correct_answers', 'score_display', 'is_daily_challenge']
    list_filter = ['is_daily_challenge', 'started_at', 'completed_at']
    search_fields = ['user__username']
    readonly_fields = ['started_at', 'completed_at']
    date_hierarchy = 'started_at'
    
    def score_display(self, obj):
        percentage = obj.score_percentage
        color = 'green' if percentage >= 70 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    score_display.short_description = 'Score'


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_preview', 'is_correct', 'time_taken', 'answered_at']
    list_filter = ['is_correct', 'answered_at', 'question__domain', 'question__difficulty']
    search_fields = ['user__username', 'question__question_text']
    readonly_fields = ['answered_at']
    date_hierarchy = 'answered_at'
    
    def question_preview(self, obj):
        return obj.question.question_text[:60] + '...' if len(obj.question.question_text) > 60 else obj.question.question_text
    question_preview.short_description = 'Question'


@admin.register(BookmarkedQuestion)
class BookmarkedQuestionAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_preview', 'tags', 'created_at']
    list_filter = ['created_at', 'question__domain']
    search_fields = ['user__username', 'question__question_text', 'notes', 'tags']
    readonly_fields = ['created_at']
    
    def question_preview(self, obj):
        return obj.question.question_text[:60] + '...' if len(obj.question.question_text) > 60 else obj.question.question_text
    question_preview.short_description = 'Question'


@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ['date', 'question_count', 'completion_count', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['date']
    filter_horizontal = ['questions']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def completion_count(self, obj):
        return obj.completions.count()
    completion_count.short_description = 'Completions'


@admin.register(DailyChallengeCompletion)
class DailyChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'score', 'total_questions', 'percentage', 'completed_at']
    list_filter = ['completed_at', 'challenge__date']
    search_fields = ['user__username']
    readonly_fields = ['completed_at']
    date_hierarchy = 'completed_at'
    
    def percentage(self, obj):
        pct = (obj.score / obj.total_questions * 100) if obj.total_questions > 0 else 0
        color = 'green' if pct >= 70 else 'orange' if pct >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, pct
        )
    percentage.short_description = 'Score %'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'achievement_type', 'requirement', 'icon']
    list_filter = ['achievement_type']
    search_fields = ['name', 'description']


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'unlocked_at']
    list_filter = ['achievement__achievement_type', 'unlocked_at']
    search_fields = ['user__username', 'achievement__name']
    readonly_fields = ['unlocked_at']
    date_hierarchy = 'unlocked_at'
