from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from .utils import get_paginator


POSTS_COUNT = 10


@cache_page(20, key_prefix="index_page")
@vary_on_cookie
def index(request):
    post_list = Post.objects.all()
    context = {
        "page_obj": get_paginator(post_list, POSTS_COUNT, request),
    }
    return render(request, "posts/index.html", context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    context = {
        "group": group,
        "page_obj": get_paginator(post_list, POSTS_COUNT, request),
    }
    return render(request, "posts/group_list.html", context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    following = request.user.is_authenticated
    if following:
        following = author.following.filter(user=request.user).exists()
    context = {
        "author": author,
        "page_obj": get_paginator(post_list, POSTS_COUNT, request),
        "following": following,
    }
    return render(request, "posts/profile.html", context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    author = post.author
    posts_count = author.posts.count()
    context = {
        "post": post,
        "author": author,
        "posts_count": posts_count,
        "form": form,
        "comments": post.comments.all(),
    }
    return render(request, "posts/post_detail.html", context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)

    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("posts:profile", username=post.author)

    context = {
        "form": form,
    }
    return render(request, "posts/post_create.html", context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect("posts:post_detail", post_id=post_id)

    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("posts:post_detail", post_id=post_id)

    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, "posts/post_create.html", context)


@login_required
def post_delete(request, post_id):
    post_to_delete = get_object_or_404(Post, pk=post_id)
    if post_to_delete.author != request.user:
        return redirect("posts:post_detail", post_id=post_id)

    if request.method == "POST":
        post_to_delete.delete()
        return redirect("posts:index")
    context = {
        "post": post_to_delete,
    }
    return render(request, "posts/post_delete.html", context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect("posts:post_detail", post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = {
        "page_obj": get_paginator(post_list, POSTS_COUNT, request),
    }
    return render(request, "posts/follow.html", context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if not (
        author == request.user
        or request.user.follower.filter(author=author).exists()
    ):
        Follow.objects.create(
            user=request.user,
            author=author,
        )
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    request.user.follower.filter(author=author).delete()
    return redirect("posts:profile", username=username)
