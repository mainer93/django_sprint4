from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone

from .forms import PostForm, UserForm, CommentForm
from .models import Post, Category, Comment
from blog.constants import Constants


class FilterMixin:
    def filtered_posts(self, queryset):
        return queryset.filter(
            category__is_published=True,
            is_published=True,
            pub_date__lte=timezone.now()
        )

    def annotated_posts(self, queryset):
        return queryset.annotate(
            comment_count=Count('comments')).order_by('-pub_date')


class ProfileView(ListView, FilterMixin):
    model = Post
    paginate_by = Constants.PAGINATION
    template_name = 'blog/profile.html'
    author = None

    def get_queryset(self):
        self.author = get_object_or_404(User, username=self.kwargs['username'])
        return self.annotated_posts(self.author.poles)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.author
        context['form'] = CommentForm()
        context['post'] = self.get_queryset().select_related('author')
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
    template_name = 'blog/category.html'
    pk_url_kwarg = 'category_slug'
    paginate_by = Constants.PAGINATION
    category = None

    def get_queryset(self):
        self.category = get_object_or_404(Category,
                                          slug=self.kwargs['category_slug'],
                                          is_published=True)
        return self.filtered_posts(self.category.posts)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostListView(ListView, FilterMixin):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = Constants.PAGINATION

    def get_queryset(self):
        queryset = self.annotated_posts(super().get_queryset())
        return self.filtered_posts(queryset)


class PostDetailView(DetailView, FilterMixin):
    model = Post
    form_class = PostForm
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        queryset = self.filtered_posts(self.annotated_posts(
            Post.objects.all())) | Post.objects.filter(
                author=self.request.user.id)
        post = get_object_or_404(queryset, pk=self.kwargs['post_id'])
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['form'] = CommentForm()
        context['comments'] = post.comments.select_related('author')
        return context


class PostsMixin:
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', post_id=post.pk)
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
        return reverse('blog:post_detail', kwargs={'post_id': self.object.pk})


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
    post_id_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', post_id=post.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    post_id_url_kwarg = 'post_id'

    def form_valid(self, form):
        form.instance.post = get_object_or_404(
            Post, pk=self.kwargs['post_id'])
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs['post_id']})


class CommentUpdateView(LoginRequiredMixin, CommentMixin, UpdateView):
    pass


class CommentDeleteView(LoginRequiredMixin, CommentMixin, DeleteView):
    pass
