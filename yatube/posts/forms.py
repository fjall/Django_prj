from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = (
            "text",
            "group",
            "image",
        )
        labels = {
            "text": "Текст поста",
            "group": "Группа поста",
            "image": "Картиночка",
        }
        help_texts = {
            "text": "^^^Наслаждайтесь возможностью набора текста^^^",
            "group": "^^^Укажите группу^^^",
            "image": "^^^Изображение для иллюстрации вашего поста^^^",
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ("text",)
        labels = {
            "text": "Текст комментария",
        }
        help_texts = {
            "text": "^^^Наслаждайтесь возможностью набора текста^^^",
        }
