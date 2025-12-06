# quiz/management/commands/create_achievements.py
from django.core.management.base import BaseCommand
from quiz.models import Achievement


class Command(BaseCommand):
    help = 'Create initial achievement badges'

    def handle(self, *args, **kwargs):
        achievements = [
            # Streak achievements
            {
                'name': '🔥 पहिलो दिन',
                'description': 'पहिलो पटक क्विज खेल्नुभयो',
                'achievement_type': 'streak',
                'icon': 'fa-fire',
                'requirement': 1
            },
            {
                'name': '🔥 ७ दिन स्ट्रिक',
                'description': 'लगातार ७ दिन क्विज खेल्नुभयो',
                'achievement_type': 'streak',
                'icon': 'fa-fire-flame-curved',
                'requirement': 7
            },
            {
                'name': '🔥 ३० दिन स्ट्रिक',
                'description': 'लगातार ३० दिन क्विज खेल्नुभयो',
                'achievement_type': 'streak',
                'icon': 'fa-fire-flame-simple',
                'requirement': 30
            },
            
            # Accuracy achievements
            {
                'name': '🎯 शुरुवात',
                'description': '५०% भन्दा माथि सटीकता',
                'achievement_type': 'accuracy',
                'icon': 'fa-bullseye',
                'requirement': 50
            },
            {
                'name': '🎯 राम्रो',
                'description': '७०% भन्दा माथि सटीकता',
                'achievement_type': 'accuracy',
                'icon': 'fa-crosshairs',
                'requirement': 70
            },
            {
                'name': '🎯 उत्कृष्ट',
                'description': '९०% भन्दा माथि सटीकता',
                'achievement_type': 'accuracy',
                'icon': 'fa-trophy',
                'requirement': 90
            },
            
            # Questions attempted
            {
                'name': '📚 शुरुवात',
                'description': '१० प्रश्न प्रयास गर्नुभयो',
                'achievement_type': 'questions',
                'icon': 'fa-book',
                'requirement': 10
            },
            {
                'name': '📚 अभ्यासकर्ता',
                'description': '१०० प्रश्न प्रयास गर्नुभयो',
                'achievement_type': 'questions',
                'icon': 'fa-book-open',
                'requirement': 100
            },
            {
                'name': '📚 विशेषज्ञ',
                'description': '५०० प्रश्न प्रयास गर्नुभयो',
                'achievement_type': 'questions',
                'icon': 'fa-graduation-cap',
                'requirement': 500
            },
            {
                'name': '📚 मास्टर',
                'description': '१००० प्रश्न प्रयास गर्नुभयो',
                'achievement_type': 'questions',
                'icon': 'fa-crown',
                'requirement': 1000
            },
            
            # Daily challenge
            {
                'name': '⭐ दैनिक च्यालेन्ज',
                'description': 'पहिलो दैनिक च्यालेन्ज पूरा गर्नुभयो',
                'achievement_type': 'daily',
                'icon': 'fa-star',
                'requirement': 1
            },
            {
                'name': '⭐ दैनिक योद्धा',
                'description': '७ दैनिक च्यालेन्ज पूरा गर्नुभयो',
                'achievement_type': 'daily',
                'icon': 'fa-star-half-stroke',
                'requirement': 7
            },
            {
                'name': '⭐ दैनिक च्याम्पियन',
                'description': '३० दैनिक च्यालेन्ज पूरा गर्नुभयो',
                'achievement_type': 'daily',
                'icon': 'fa-medal',
                'requirement': 30
            },
        ]
        
        created_count = 0
        for achievement_data in achievements:
            achievement, created = Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults=achievement_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created achievement: {achievement.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal achievements created: {created_count}')
        )
