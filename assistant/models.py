from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SavedDraft(models.Model):
    """Store user drafts for later editing"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drafts')
    title = models.CharField(max_length=200, default="Untitled Draft")
    original_text = models.TextField()
    transformed_text = models.TextField(blank=True)
    transformation_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_favorite = models.BooleanField(default=False)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    class Meta:
        verbose_name = "Saved Draft"
        verbose_name_plural = "Saved Drafts"
        ordering = ['-updated_at']


class WritingTemplate(models.Model):
    """Predefined writing templates"""
    CATEGORY_CHOICES = [
        ('email', 'Email'),
        ('letter', 'Letter'),
        ('essay', 'Essay'),
        ('report', 'Report'),
        ('creative', 'Creative Writing'),
        ('business', 'Business'),
        ('academic', 'Academic'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    template_text = models.TextField()
    placeholder_fields = models.JSONField(default=list, help_text="List of placeholder fields")
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    class Meta:
        verbose_name = "Writing Template"
        verbose_name_plural = "Writing Templates"
        ordering = ['-usage_count', 'name']


class TransformationHistory(models.Model):
    """Track all text transformations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transformations')
    original_text = models.TextField()
    transformed_text = models.TextField()
    transformation_type = models.CharField(max_length=50)
    character_count_before = models.IntegerField()
    character_count_after = models.IntegerField()
    word_count_before = models.IntegerField()
    word_count_after = models.IntegerField()
    processing_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.transformation_type} - {self.created_at.date()}"
    
    @property
    def compression_ratio(self):
        if self.character_count_before == 0:
            return 0
        return round((self.character_count_after / self.character_count_before) * 100, 2)
    
    class Meta:
        verbose_name = "Transformation History"
        verbose_name_plural = "Transformation Histories"
        ordering = ['-created_at']


class UserWritingStats(models.Model):
    """Writing statistics for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='writing_stats')
    total_transformations = models.IntegerField(default=0)
    total_characters_processed = models.BigIntegerField(default=0)
    total_words_processed = models.BigIntegerField(default=0)
    favorite_transformation = models.CharField(max_length=50, blank=True)
    total_drafts_saved = models.IntegerField(default=0)
    total_templates_used = models.IntegerField(default=0)
    average_processing_time_ms = models.FloatField(default=0.0)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Writing Stats"
    
    class Meta:
        verbose_name = "User Writing Stats"
        verbose_name_plural = "User Writing Stats"


class TextComparison(models.Model):
    """Store text comparisons for review"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comparisons')
    original_text = models.TextField()
    transformed_text = models.TextField()
    transformation_type = models.CharField(max_length=50)
    differences_highlighted = models.JSONField(default=dict, help_text="Highlighted differences")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Comparison - {self.created_at.date()}"
    
    class Meta:
        verbose_name = "Text Comparison"
        verbose_name_plural = "Text Comparisons"
        ordering = ['-created_at']
