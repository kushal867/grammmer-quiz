# assistant/admin_enhanced.py - Enhanced admin configuration for Assistant
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SavedDraft, WritingTemplate, TransformationHistory,
    UserWritingStats, TextComparison
)


@admin.register(SavedDraft)
class SavedDraftAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'transformation_type', 'favorite_badge', 'tags_display', 'updated_at']
    list_filter = ['is_favorite', 'transformation_type', 'created_at', 'updated_at']
    search_fields = ['title', 'user__username', 'original_text', 'tags']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'is_favorite', 'tags')
        }),
        ('Content', {
            'fields': ('original_text', 'transformed_text', 'transformation_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def favorite_badge(self, obj):
        if obj.is_favorite:
            return format_html('<span style="color: #F59E0B; font-size: 18px;">⭐</span>')
        return '-'
    favorite_badge.short_description = 'Favorite'
    
    def tags_display(self, obj):
        if obj.tags:
            tags = obj.tags.split(',')
            tag_html = ''.join([
                f'<span style="background: #7C3AED; color: white; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-size: 11px;">{tag.strip()}</span>'
                for tag in tags
            ])
            return format_html(tag_html)
        return '-'
    tags_display.short_description = 'Tags'


@admin.register(WritingTemplate)
class WritingTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_badge', 'usage_count_display', 'public_badge', 'created_by', 'created_at']
    list_filter = ['category', 'is_public', 'created_at']
    search_fields = ['name', 'description', 'template_text']
    readonly_fields = ['usage_count', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'is_public', 'created_by')
        }),
        ('Template Content', {
            'fields': ('template_text', 'placeholder_fields')
        }),
        ('Statistics', {
            'fields': ('usage_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_badge(self, obj):
        colors = {
            'email': '#10B981',
            'letter': '#7C3AED',
            'essay': '#F59E0B',
            'report': '#EF4444',
            'creative': '#EC4899',
            'business': '#06B6D4',
            'academic': '#8B5CF6',
            'other': '#6B7280'
        }
        color = colors.get(obj.category, '#6B7280')
        return format_html(
            f'<span style="background: {color}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{obj.get_category_display()}</span>'
        )
    category_badge.short_description = 'Category'
    
    def usage_count_display(self, obj):
        if obj.usage_count > 100:
            return format_html(f'<span style="color: #10B981; font-weight: bold;">🔥 {obj.usage_count}</span>')
        elif obj.usage_count > 50:
            return format_html(f'<span style="color: #F59E0B; font-weight: bold;">⭐ {obj.usage_count}</span>')
        return obj.usage_count
    usage_count_display.short_description = 'Usage'
    
    def public_badge(self, obj):
        if obj.is_public:
            return format_html('<span style="color: #10B981;">✓ Public</span>')
        return format_html('<span style="color: #6B7280;">✗ Private</span>')
    public_badge.short_description = 'Visibility'


@admin.register(TransformationHistory)
class TransformationHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'transformation_type', 'word_change_display', 'compression_display', 'processing_time_display', 'created_at']
    list_filter = ['transformation_type', 'created_at']
    search_fields = ['user__username', 'original_text', 'transformed_text']
    readonly_fields = ['created_at', 'compression_ratio']
    date_hierarchy = 'created_at'
    
    def word_change_display(self, obj):
        change = obj.word_count_after - obj.word_count_before
        if change > 0:
            return format_html(f'<span style="color: #10B981;">+{change} words</span>')
        elif change < 0:
            return format_html(f'<span style="color: #EF4444;">{change} words</span>')
        return '0 words'
    word_change_display.short_description = 'Word Change'
    
    def compression_display(self, obj):
        ratio = obj.compression_ratio
        if ratio < 80:
            color = '#10B981'  # Compressed
        elif ratio > 120:
            color = '#7C3AED'  # Expanded
        else:
            color = '#6B7280'  # Similar
        return format_html(f'<span style="color: {color}; font-weight: bold;">{ratio}%</span>')
    compression_display.short_description = 'Compression'
    
    def processing_time_display(self, obj):
        if obj.processing_time_ms:
            if obj.processing_time_ms < 1000:
                return format_html(f'<span style="color: #10B981;">{obj.processing_time_ms}ms</span>')
            else:
                seconds = obj.processing_time_ms / 1000
                return format_html(f'<span style="color: #F59E0B;">{seconds:.2f}s</span>')
        return '-'
    processing_time_display.short_description = 'Processing Time'


@admin.register(UserWritingStats)
class UserWritingStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_transformations', 'words_processed_display', 'favorite_transformation_badge', 'avg_time_display', 'last_activity']
    list_filter = ['favorite_transformation', 'last_activity']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'last_activity']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Transformation Statistics', {
            'fields': ('total_transformations', 'favorite_transformation', 'average_processing_time_ms')
        }),
        ('Content Statistics', {
            'fields': ('total_characters_processed', 'total_words_processed')
        }),
        ('Usage Statistics', {
            'fields': ('total_drafts_saved', 'total_templates_used')
        }),
        ('Activity', {
            'fields': ('last_activity', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def words_processed_display(self, obj):
        words = obj.total_words_processed
        if words > 1000000:
            return format_html(f'<span style="color: #7C3AED; font-weight: bold;">🏆 {words:,}</span>')
        elif words > 100000:
            return format_html(f'<span style="color: #10B981; font-weight: bold;">⭐ {words:,}</span>')
        return f'{words:,}'
    words_processed_display.short_description = 'Words Processed'
    
    def favorite_transformation_badge(self, obj):
        if obj.favorite_transformation:
            return format_html(
                f'<span style="background: #F59E0B; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{obj.favorite_transformation}</span>'
            )
        return '-'
    favorite_transformation_badge.short_description = 'Favorite'
    
    def avg_time_display(self, obj):
        if obj.average_processing_time_ms:
            return f'{obj.average_processing_time_ms:.0f}ms'
        return '-'
    avg_time_display.short_description = 'Avg Time'


@admin.register(TextComparison)
class TextComparisonAdmin(admin.ModelAdmin):
    list_display = ['user', 'transformation_type', 'changes_summary', 'created_at']
    list_filter = ['transformation_type', 'created_at']
    search_fields = ['user__username', 'original_text', 'transformed_text']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def changes_summary(self, obj):
        diffs = obj.differences_highlighted
        added = len(diffs.get('added_lines', []))
        removed = len(diffs.get('removed_lines', []))
        
        summary = []
        if added > 0:
            summary.append(f'<span style="color: #10B981;">+{added}</span>')
        if removed > 0:
            summary.append(f'<span style="color: #EF4444;">-{removed}</span>')
        
        return format_html(' '.join(summary)) if summary else '-'
    changes_summary.short_description = 'Changes'
