from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile for tracking quiz statistics and progress"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_questions_attempted = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    last_daily_challenge = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def accuracy(self):
        if self.total_questions_attempted == 0:
            return 0
        return round((self.correct_answers / self.total_questions_attempted) * 100, 2)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class Question(models.Model):
    """Store AI-generated questions for reuse and review"""
    DIFFICULTY_CHOICES = [
        ('सजिलो', 'Easy'),
        ('मध्यम', 'Medium'),
        ('कठिन', 'Hard'),
    ]
    
    domain = models.CharField(max_length=100, db_index=True)
    topic = models.CharField(max_length=200, db_index=True)
    difficulty = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, db_index=True)
    question_text = models.TextField()
    options = models.JSONField()  # Store as JSON array
    correct_answer = models.CharField(max_length=10)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    times_used = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.domain} - {self.question_text[:50]}..."
    
    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'difficulty']),
            models.Index(fields=['is_approved', 'is_reviewed']),
        ]


class QuizAttempt(models.Model):
    """Track individual quiz sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    is_daily_challenge = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.started_at.date()}"
    
    @property
    def score_percentage(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 2)
    
    class Meta:
        verbose_name = "Quiz Attempt"
        verbose_name_plural = "Quiz Attempts"
        ordering = ['-started_at']


class UserAnswer(models.Model):
    """Track individual answers for detailed analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers', null=True, blank=True)
    selected_answer = models.CharField(max_length=10)
    is_correct = models.BooleanField()
    time_taken = models.IntegerField(help_text="Time in seconds", null=True, blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {'✓' if self.is_correct else '✗'}"
    
    class Meta:
        verbose_name = "User Answer"
        verbose_name_plural = "User Answers"
        ordering = ['-answered_at']


class BookmarkedQuestion(models.Model):
    """User's saved questions for later review"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Personal notes about this question")
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    def __str__(self):
        return f"{self.user.username} - {self.question.question_text[:30]}..."
    
    class Meta:
        verbose_name = "Bookmarked Question"
        verbose_name_plural = "Bookmarked Questions"
        unique_together = ['user', 'question']
        ordering = ['-created_at']


class DailyChallenge(models.Model):
    """Daily challenge questions"""
    date = models.DateField(unique=True, db_index=True)
    questions = models.ManyToManyField(Question, related_name='daily_challenges')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Daily Challenge - {self.date}"
    
    class Meta:
        verbose_name = "Daily Challenge"
        verbose_name_plural = "Daily Challenges"
        ordering = ['-date']


class DailyChallengeCompletion(models.Model):
    """Track user completion of daily challenges"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_completions')
    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.date}"
    
    class Meta:
        verbose_name = "Daily Challenge Completion"
        verbose_name_plural = "Daily Challenge Completions"
        unique_together = ['user', 'challenge']
        ordering = ['-completed_at']


class Achievement(models.Model):
    """Achievement badges for user engagement"""
    ACHIEVEMENT_TYPES = [
        ('streak', 'Streak'),
        ('accuracy', 'Accuracy'),
        ('questions', 'Questions'),
        ('daily', 'Daily Challenge'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class")
    requirement = models.IntegerField(help_text="Requirement value to unlock")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"


class UserAchievement(models.Model):
    """Track user's unlocked achievements"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
    
    class Meta:
        verbose_name = "User Achievement"
        verbose_name_plural = "User Achievements"
        unique_together = ['user', 'achievement']
        ordering = ['-unlocked_at']


# Signal to automatically create UserProfile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class QuestionRating(models.Model):
    """User ratings and feedback for questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_ratings')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    feedback = models.TextField(blank=True, help_text="Optional feedback about the question")
    is_too_easy = models.BooleanField(default=False)
    is_too_hard = models.BooleanField(default=False)
    is_unclear = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.question.id} - {self.rating}★"
    
    class Meta:
        verbose_name = "Question Rating"
        verbose_name_plural = "Question Ratings"
        unique_together = ['user', 'question']
        ordering = ['-created_at']


class TimedQuizSession(models.Model):
    """Track timed quiz sessions"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timed_sessions')
    duration_minutes = models.IntegerField(default=30, help_text="Quiz duration in minutes")
    questions_count = models.IntegerField(default=20)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    score = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.duration_minutes}min - {self.status}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        if self.status == 'completed':
            return False
        elapsed = timezone.now() - self.started_at
        return elapsed.total_seconds() > (self.duration_minutes * 60)
    
    class Meta:
        verbose_name = "Timed Quiz Session"
        verbose_name_plural = "Timed Quiz Sessions"
        ordering = ['-started_at']


class UserPreferences(models.Model):
    """User preferences and settings"""
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]
    
    DIFFICULTY_PREFERENCE = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('adaptive', 'Adaptive'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    preferred_difficulty = models.CharField(max_length=20, choices=DIFFICULTY_PREFERENCE, default='adaptive')
    enable_sound = models.BooleanField(default=True)
    enable_animations = models.BooleanField(default=True)
    show_explanations = models.BooleanField(default=True)
    auto_next_question = models.BooleanField(default=False)
    questions_per_session = models.IntegerField(default=20)
    enable_keyboard_shortcuts = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Preferences"
    
    class Meta:
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"


class PerformanceMetrics(models.Model):
    """Detailed performance analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='performance_metrics')
    date = models.DateField(auto_now_add=True)
    questions_attempted = models.IntegerField(default=0)
    questions_correct = models.IntegerField(default=0)
    average_time_per_question = models.FloatField(default=0.0, help_text="Average time in seconds")
    domains_covered = models.JSONField(default=dict, help_text="Domain-wise performance")
    difficulty_breakdown = models.JSONField(default=dict, help_text="Performance by difficulty")
    streak_count = models.IntegerField(default=0)
    study_time_minutes = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"
    
    @property
    def accuracy_percentage(self):
        if self.questions_attempted == 0:
            return 0
        return round((self.questions_correct / self.questions_attempted) * 100, 2)
    
    class Meta:
        verbose_name = "Performance Metric"
        verbose_name_plural = "Performance Metrics"
        unique_together = ['user', 'date']
        ordering = ['-date']


class QuestionCache(models.Model):
    """Cache frequently used questions for performance"""
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='cache')
    cache_key = models.CharField(max_length=255, unique=True, db_index=True)
    cached_data = models.JSONField(help_text="Serialized question data")
    hit_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cache: {self.cache_key} ({self.hit_count} hits)"
    
    class Meta:
        verbose_name = "Question Cache"
        verbose_name_plural = "Question Caches"
        ordering = ['-hit_count']


class Leaderboard(models.Model):
    """Global and weekly leaderboards"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('all_time', 'All Time'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, db_index=True)
    period_start = models.DateField()
    rank = models.IntegerField()
    score = models.IntegerField()
    questions_answered = models.IntegerField()
    accuracy = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"#{self.rank} {self.user.username} - {self.period}"
    
    class Meta:
        verbose_name = "Leaderboard Entry"
        verbose_name_plural = "Leaderboard Entries"
        unique_together = ['user', 'period', 'period_start']
        ordering = ['period', 'rank']
        indexes = [
            models.Index(fields=['period', 'rank']),
        ]


# Signal to create UserPreferences when User is created
@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        UserPreferences.objects.create(user=instance)
