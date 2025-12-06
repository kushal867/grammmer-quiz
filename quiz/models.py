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
