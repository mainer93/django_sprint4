from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import Http404

from .forms import PostForm, UserForm, CommentForm
from .models import Post, Category, Comment
from blog.constants import Constants


class FilterMixin:
    def get_posts(self):
        return Post.objects.filter(
            category__is_published=True,
            is_published=True,
            pub_date__lte=timezone.now()
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')


class ProfileView(DetailView, FilterMixin):
    model = User
    form_class = UserForm
    paginate_by = Constants.PAGINATION
    template_name = 'blog/profile.html'
    slug_url_kwarg = 'username'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_queryset(self, author):
        if self.request.user == author:
            return Post.objects.filter(
                author=author).annotate(
                    comment_count=Count('comments')).order_by('-pub_date')
        return self.get_posts().filter(
            author=author).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        author = self.get_object()
        posts = self.get_queryset(author)
        paginator = Paginator(posts, Constants.PAGINATION)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user.username})


class CategoryPostListView(ListView, FilterMixin):
    model = Post
    form_class = PostForm
    template_name = 'blog/category.html'
    pk_url_kwarg = 'category_slug'
    paginate_by = Constants.PAGINATION

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category,
                                          slug=self.kwargs['category_slug'],
                                          is_published=True)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.category.posts.filter(is_published=True,
                                          pub_date__lte=timezone.now()
                                          ).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostListView(ListView, FilterMixin):
    model = Post
    form_class = PostForm
    template_name = 'blog/index.html'
    paginate_by = Constants.PAGINATION

    def get_queryset(self):
        return self.get_posts()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = Post.objects.count()
        return context


class PostDetailView(DetailView, FilterMixin):
    model = Post
    form_class = PostForm
    template_name = 'blog/detail.html'

    def get_posts(self):
        return super().get_posts() | Q(
            author=self.request.user.id
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()

        if (
            self.request.user == post.author
            or (
                post.is_published
                and post.pub_date <= timezone.now()
                and post.category.is_published
            )
        ):
            context['form'] = CommentForm()
            context['comments'] = self.object.comments.select_related('author')
            return context

        raise Http404("У данного пользователя нет прав для просмотра"
                      " данного неопубликованного поста")


class PostsMixin:
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', pk=post.pk)
        return super().dispatch(request, *args, **kwargs)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile',
                       kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, PostsMixin, UpdateView):

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'pk': self.kwargs['post_id']})


class PostDeleteView(LoginRequiredMixin, PostsMixin, DeleteView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['post'] = post
        context['form'] = PostForm(instance=post)
        return context

    def get_success_url(self):
        return reverse('blog:index')


class CommentMixin:
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', pk=post.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'pk': self.kwargs['post_id']})


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def form_valid(self, form):
        form.instance.post = get_object_or_404(
            Post, pk=self.kwargs['post_id'])
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'pk': self.kwargs['post_id']})


class CommentUpdateView(LoginRequiredMixin, CommentMixin, UpdateView):
    pass


class CommentDeleteView(LoginRequiredMixin, CommentMixin, DeleteView):
    pass
