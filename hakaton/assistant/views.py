from django.views.generic import TemplateView

# Демо-данные каркаса (заменятся моделью и API)
DEMO_CHATS = [
    {
        'id': '1',
        'title': 'Мероприятия на неделе',
        'preview': 'Какие мероприятия проходят на этой неделе?',
        'updated': 'Сегодня, 14:32',
    },
    {
        'id': '2',
        'title': 'Материалы вебинара',
        'preview': 'Где найти материалы по прошедшему вебинару?',
        'updated': 'Вчера',
    },
    {
        'id': '3',
        'title': 'Запись на программу',
        'preview': 'Как записаться на образовательную программу?',
        'updated': '12 мая',
    },
]

DEMO_MESSAGES = {
    '1': [
        {
            'role': 'user',
            'text': 'Какие мероприятия проходят на этой неделе?',
            'time': '14:28',
        },
        {
            'role': 'assistant',
            'text': (
                'На этой неделе в просветительской среде запланированы: '
                'лекция «Наука и город» (вторник, 18:00), мастер-класс для школьников '
                '(четверг, 15:00) и открытая встреча с резидентами (суббота, 12:00).'
            ),
            'time': '14:29',
        },
        {
            'role': 'user',
            'text': 'А где посмотреть полную афишу?',
            'time': '14:31',
        },
        {
            'role': 'assistant',
            'text': (
                'Полная афиша доступна в разделе «Мероприятия» на главной странице. '
                'Там же можно отфильтровать события по дате и формату — очно или онлайн.'
            ),
            'time': '14:32',
        },
    ],
    '2': [
        {
            'role': 'user',
            'text': 'Где найти материалы по прошедшему вебинару?',
            'time': 'Вчера, 11:05',
        },
        {
            'role': 'assistant',
            'text': (
                'Запись и презентация обычно появляются в карточке мероприятия '
                'в течение 1–2 рабочих дней после эфира. Откройте вебинар в афише — '
                'блок «Материалы» будет внизу страницы.'
            ),
            'time': 'Вчера, 11:06',
        },
    ],
    '3': [
        {
            'role': 'user',
            'text': 'Как записаться на образовательную программу?',
            'time': '12 мая, 09:15',
        },
        {
            'role': 'assistant',
            'text': (
                'Выберите программу в каталоге, нажмите «Подать заявку» и заполните форму. '
                'После проверки заявки на почту придёт уведомление о статусе.'
            ),
            'time': '12 мая, 09:16',
        },
        {
            'role': 'user',
            'text': 'Сколько ждать ответа?',
            'time': '12 мая, 09:18',
        },
        {
            'role': 'assistant',
            'text': 'Стандартный срок рассмотрения — до 5 рабочих дней. Статус заявки виден в личном кабинете.',
            'time': '12 мая, 09:18',
        },
    ],
}


class ChatView(TemplateView):
    """Страница диалога с ассистентом (UI-каркас, без логики ответов)."""

    template_name = 'assistant/chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chats = DEMO_CHATS
        active_id = self.request.GET.get('chat') or (chats[0]['id'] if chats else None)
        active_chat = next((c for c in chats if c['id'] == active_id), chats[0] if chats else None)
        messages = DEMO_MESSAGES.get(active_chat['id'], []) if active_chat else []
        context['chats'] = chats
        context['active_chat'] = active_chat
        context['active_chat_id'] = active_chat['id'] if active_chat else None
        context['messages'] = messages
        return context
