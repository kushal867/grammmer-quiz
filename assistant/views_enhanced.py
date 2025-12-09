# assistant/views_enhanced.py - Enhanced features for Kushal Writer
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import logging
import difflib

from .models import (
    SavedDraft, WritingTemplate, TransformationHistory,
    UserWritingStats, TextComparison
)

logger = logging.getLogger(__name__)


# ==================== DRAFT MANAGEMENT ====================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_save_draft(request):
    """Save a draft"""
    try:
        data = json.loads(request.body)
        title = data.get('title', 'Untitled Draft')
        original_text = data.get('original_text', '')
        transformed_text = data.get('transformed_text', '')
        transformation_type = data.get('transformation_type', '')
        tags = data.get('tags', '')
        
        draft = SavedDraft.objects.create(
            user=request.user,
            title=title,
            original_text=original_text,
            transformed_text=transformed_text,
            transformation_type=transformation_type,
            tags=tags
        )
        
        # Update user stats
        stats, created = UserWritingStats.objects.get_or_create(user=request.user)
        stats.total_drafts_saved += 1
        stats.save()
        
        return JsonResponse({
            'success': True,
            'draft_id': draft.id,
            'message': 'Draft saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving draft: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def api_get_drafts(request):
    """Get user's saved drafts"""
    try:
        drafts = SavedDraft.objects.filter(user=request.user).order_by('-updated_at')
        
        drafts_data = [
            {
                'id': draft.id,
                'title': draft.title,
                'original_text': draft.original_text[:100] + '...' if len(draft.original_text) > 100 else draft.original_text,
                'transformation_type': draft.transformation_type,
                'created_at': draft.created_at.isoformat(),
                'updated_at': draft.updated_at.isoformat(),
                'is_favorite': draft.is_favorite,
                'tags': draft.tags.split(',') if draft.tags else []
            }
            for draft in drafts
        ]
        
        return JsonResponse({
            'success': True,
            'drafts': drafts_data,
            'total': len(drafts_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting drafts: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def api_get_draft(request, draft_id):
    """Get a specific draft"""
    try:
        draft = SavedDraft.objects.get(id=draft_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'draft': {
                'id': draft.id,
                'title': draft.title,
                'original_text': draft.original_text,
                'transformed_text': draft.transformed_text,
                'transformation_type': draft.transformation_type,
                'created_at': draft.created_at.isoformat(),
                'updated_at': draft.updated_at.isoformat(),
                'is_favorite': draft.is_favorite,
                'tags': draft.tags.split(',') if draft.tags else []
            }
        })
        
    except SavedDraft.DoesNotExist:
        return JsonResponse({'error': 'Draft not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting draft: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@login_required
def api_delete_draft(request, draft_id):
    """Delete a draft"""
    try:
        draft = SavedDraft.objects.get(id=draft_id, user=request.user)
        draft.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Draft deleted successfully'
        })
        
    except SavedDraft.DoesNotExist:
        return JsonResponse({'error': 'Draft not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== TEMPLATES ====================

@require_http_methods(["GET"])
def api_get_templates(request):
    """Get all public templates"""
    try:
        category = request.GET.get('category', None)
        
        templates = WritingTemplate.objects.filter(is_public=True)
        
        if category:
            templates = templates.filter(category=category)
        
        templates = templates.order_by('-usage_count', 'name')
        
        templates_data = [
            {
                'id': template.id,
                'name': template.name,
                'category': template.category,
                'description': template.description,
                'template_text': template.template_text,
                'placeholder_fields': template.placeholder_fields,
                'usage_count': template.usage_count
            }
            for template in templates
        ]
        
        return JsonResponse({
            'success': True,
            'templates': templates_data,
            'total': len(templates_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_use_template(request):
    """Use a template and increment usage count"""
    try:
        data = json.loads(request.body)
        template_id = data.get('template_id')
        
        template = WritingTemplate.objects.get(id=template_id)
        template.usage_count += 1
        template.save()
        
        # Update user stats
        stats, created = UserWritingStats.objects.get_or_create(user=request.user)
        stats.total_templates_used += 1
        stats.save()
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'template_text': template.template_text,
                'placeholder_fields': template.placeholder_fields
            }
        })
        
    except WritingTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)
    except Exception as e:
        logger.error(f"Error using template: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== TEXT COMPARISON ====================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_compare_text(request):
    """Compare original and transformed text"""
    try:
        data = json.loads(request.body)
        original_text = data.get('original_text', '')
        transformed_text = data.get('transformed_text', '')
        transformation_type = data.get('transformation_type', '')
        
        # Generate diff
        diff = list(difflib.unified_diff(
            original_text.splitlines(keepends=True),
            transformed_text.splitlines(keepends=True),
            lineterm=''
        ))
        
        # Highlight differences
        differences = {
            'added_lines': [],
            'removed_lines': [],
            'changed_lines': []
        }
        
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                differences['added_lines'].append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                differences['removed_lines'].append(line[1:])
        
        # Save comparison
        comparison = TextComparison.objects.create(
            user=request.user,
            original_text=original_text,
            transformed_text=transformed_text,
            transformation_type=transformation_type,
            differences_highlighted=differences
        )
        
        # Calculate statistics
        original_words = len(original_text.split())
        transformed_words = len(transformed_text.split())
        word_change = transformed_words - original_words
        word_change_percent = (word_change / original_words * 100) if original_words > 0 else 0
        
        return JsonResponse({
            'success': True,
            'comparison_id': comparison.id,
            'differences': differences,
            'statistics': {
                'original_words': original_words,
                'transformed_words': transformed_words,
                'word_change': word_change,
                'word_change_percent': round(word_change_percent, 2),
                'original_chars': len(original_text),
                'transformed_chars': len(transformed_text)
            }
        })
        
    except Exception as e:
        logger.error(f"Error comparing text: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== TRANSFORMATION HISTORY ====================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_save_transformation(request):
    """Save transformation to history"""
    try:
        data = json.loads(request.body)
        original_text = data.get('original_text', '')
        transformed_text = data.get('transformed_text', '')
        transformation_type = data.get('transformation_type', '')
        processing_time_ms = data.get('processing_time_ms', 0)
        
        history = TransformationHistory.objects.create(
            user=request.user,
            original_text=original_text,
            transformed_text=transformed_text,
            transformation_type=transformation_type,
            character_count_before=len(original_text),
            character_count_after=len(transformed_text),
            word_count_before=len(original_text.split()),
            word_count_after=len(transformed_text.split()),
            processing_time_ms=processing_time_ms
        )
        
        # Update user stats
        stats, created = UserWritingStats.objects.get_or_create(user=request.user)
        stats.total_transformations += 1
        stats.total_characters_processed += len(original_text)
        stats.total_words_processed += len(original_text.split())
        
        # Update average processing time
        if stats.average_processing_time_ms == 0:
            stats.average_processing_time_ms = processing_time_ms
        else:
            stats.average_processing_time_ms = (
                (stats.average_processing_time_ms * (stats.total_transformations - 1) + processing_time_ms)
                / stats.total_transformations
            )
        
        # Update favorite transformation
        transformation_counts = TransformationHistory.objects.filter(
            user=request.user
        ).values('transformation_type').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        if transformation_counts:
            stats.favorite_transformation = transformation_counts['transformation_type']
        
        stats.save()
        
        return JsonResponse({
            'success': True,
            'history_id': history.id,
            'message': 'Transformation saved to history'
        })
        
    except Exception as e:
        logger.error(f"Error saving transformation: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def api_get_transformation_history(request):
    """Get transformation history"""
    try:
        limit = int(request.GET.get('limit', 50))
        transformation_type = request.GET.get('type', None)
        
        history = TransformationHistory.objects.filter(user=request.user)
        
        if transformation_type:
            history = history.filter(transformation_type=transformation_type)
        
        history = history.order_by('-created_at')[:limit]
        
        history_data = [
            {
                'id': item.id,
                'transformation_type': item.transformation_type,
                'original_text': item.original_text[:100] + '...' if len(item.original_text) > 100 else item.original_text,
                'transformed_text': item.transformed_text[:100] + '...' if len(item.transformed_text) > 100 else item.transformed_text,
                'compression_ratio': item.compression_ratio,
                'created_at': item.created_at.isoformat()
            }
            for item in history
        ]
        
        return JsonResponse({
            'success': True,
            'history': history_data,
            'total': len(history_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting transformation history: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== WRITING STATISTICS ====================

@require_http_methods(["GET"])
@login_required
def api_get_writing_stats(request):
    """Get user writing statistics"""
    try:
        stats, created = UserWritingStats.objects.get_or_create(user=request.user)
        
        # Get recent activity
        recent_transformations = TransformationHistory.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        # Get transformation type breakdown
        type_breakdown = {}
        for item in TransformationHistory.objects.filter(user=request.user):
            if item.transformation_type not in type_breakdown:
                type_breakdown[item.transformation_type] = 0
            type_breakdown[item.transformation_type] += 1
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_transformations': stats.total_transformations,
                'total_characters_processed': stats.total_characters_processed,
                'total_words_processed': stats.total_words_processed,
                'favorite_transformation': stats.favorite_transformation,
                'total_drafts_saved': stats.total_drafts_saved,
                'total_templates_used': stats.total_templates_used,
                'average_processing_time_ms': round(stats.average_processing_time_ms, 2),
                'last_activity': stats.last_activity.isoformat()
            },
            'type_breakdown': type_breakdown,
            'recent_activity': [
                {
                    'type': item.transformation_type,
                    'words_before': item.word_count_before,
                    'words_after': item.word_count_after,
                    'created_at': item.created_at.isoformat()
                }
                for item in recent_transformations
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting writing stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== PAGES ====================

@login_required
def drafts_page(request):
    """Drafts management page"""
    return render(request, 'drafts.html')


@login_required
def writing_stats_page(request):
    """Writing statistics page"""
    return render(request, 'writing_stats.html')


def templates_page(request):
    """Templates library page"""
    return render(request, 'templates.html')


# Import Count for transformation history
from django.db.models import Count
