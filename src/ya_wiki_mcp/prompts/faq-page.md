---
description: Шаблон FAQ-страницы с раскрывающимися блоками
arguments:
  - name: title
    description: Название раздела FAQ
    required: true
---
# {title}

{% note info "Как пользоваться" %}

Нажмите на вопрос, чтобы увидеть ответ.

{% endnote %}

{% cut "Вопрос 1?" %}

Ответ на вопрос 1.

{% endcut %}

{% cut "Вопрос 2?" %}

Ответ на вопрос 2.

{% endcut %}

{% cut "Вопрос 3?" %}

Ответ на вопрос 3.

{% endcut %}
