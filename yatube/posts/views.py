from genericpath import exists
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.shortcuts import redirect, render, get_object_or_404
from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow
from .utils import page_list


@cache_page(20, key_prefix='index_page')
def index(request):
    """Главная страница."""
    post_list = Post.objects.select_related('author', 'group')
    page_obj = page_list(post_list, request)
    return render(request, 'posts/index.html', {'page_obj': page_obj})


def group_posts(request, slug):
    """вывод записей одной из групп. """
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author', 'group')
    page_obj = page_list(posts, request)
    return render(request, 'posts/group_list.html', {'group': group,
                                                     'page_obj': page_obj})


def profile(request, username):
    """вывод списка всех записей пользователя. """
    user = get_object_or_404(User, username=username)
    post_list = user.posts.select_related('author', 'group')
    page_obj = page_list(post_list, request)
    following = False
    if request.user.is_authenticated:
        follow = Follow.objects.filter(user=request.user, author=user)
        if follow.exists():
            following = True
    return render(request, 'posts/profile.html', {
        'author': user,
        'page_obj': page_obj,
        'following': following,
    })


def post_detail(request, post_id):
    """подробная информация о записи. """
    post = get_object_or_404(Post, pk=post_id)
    form_comment = CommentForm(request.POST or None)
    comments = post.comments.all()
    return render(
        request,
        'posts/post_detail.html',
        {'post_detail': post,
         'form': form_comment,
         'comments': comments
         }
    )


@login_required
def post_create(request):
    """добавление новой записи в базу. """
    form = PostForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', request.user.username)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """редактирование записи. """
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id)
    return render(
        request,
        'posts/create_post.html',
        {
            'form': form,
            'is_edit': True,
            'post_id': post_id
        }
    )


@login_required
def add_comment(request, post_id):
    """добавление комментария к записи"""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user

    post_list = Post.objects.filter(author__following__user=request.user)
    page_obj = page_list(post_list, request)
    return render(request, 'posts/follow.html', {'page_obj': page_obj})

#def follow_index(request):
#    """ Страница подписки. Показывает последние опубликованные статьи авторов,
#    на которых подписан пользователь."""
#    follows = Follow.objects.filter(user=request.user)
#    authors = []
#    for i in follows:
#        print(i)
#        authors.extend(i.author)
#    posts = Post.objects.filter(author__in=authors)

# filter(author__following__user= ..


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    # user- подписчик,author - подписываемый
    follower = request.user
    followed = User.objects.get(username=username)
    follower_exists = Follow.objects.filter(user=request.user, author=followed)
    if follower != followed and not follower_exists.exists():
        Follow.objects.create(user=request.user, author=followed)
#    print(username)
#    print(follower)
#    print(followed)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    followed = User.objects.get(username=username)
    if Follow.objects.filter(user=request.user, author=followed).exists():
        Follow.objects.get(user=request.user, author=followed).delete()
    return redirect('posts:profile', username=username)
