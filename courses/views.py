from typing import Any, Dict
from django.shortcuts import render, redirect,HttpResponseRedirect
import datetime
from django.contrib.auth.mixins import (LoginRequiredMixin,
                                        PermissionRequiredMixin)
from django.urls import reverse
from django.contrib import messages
from django.views import generic
from django.shortcuts import get_object_or_404
from users.models import User
from courses.models import Course, Enrollment, Lesson, Chapter, CompletedCourse
from assignments.models import Assignment, Quiz
from resources.models import Resource
from .models import CompletedLesson
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from .models import Lesson
import json
from django.views import View
from django.http import JsonResponse
from .models import CompletedLesson, Course
from .forms import CreateChapterForm, CreateLessonForm, UpdateChapterForm, UpdateLessonForm, UpdateCourseForm

# Create your views here.
class CreateCourse(LoginRequiredMixin, generic.CreateView):
    fields = ('course_name', 'course_description')
    model = Course

    def get(self, request,*args, **kwargs):
        self.object = None
        context_dict = self.get_context_data()
        context_dict.update(user_type=self.request.user.user_type)
        return self.render_to_response(context_dict)
    
    def form_valid(self, form):
        form.instance.teacher = self.request.user
        return super(CreateCourse, self).form_valid(form)
    
class CreateChapterView(LoginRequiredMixin, generic.CreateView):
    model = Chapter
    form_class = CreateChapterForm
    template_name = 'courses/create_chapter.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    
    def form_valid(self, form):
        user_object = get_object_or_404(User, username=self.request.user.username)
        form.instance.teacher = user_object
        return super().form_valid(form)
    def get_success_url(self):
        url = reverse('courses:list')
        return url

class CreateLessonView(LoginRequiredMixin, generic.CreateView):
    form_class = CreateLessonForm
    template_name = 'courses/create_lesson.html'
    success_url = '/all/'
    
    def get_from_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    def form_valid(self, form):
        user_object = get_object_or_404(User, username=self.request.user.username)
        form.instance.teacher = user_object
        return super().form_valid(form)
    
class CourseDetail(generic.DetailView):
    model = Course
    
    def get_context_data(self, **kwargs):
        course = Course.objects.get(pk=self.kwargs['pk']) 
        
        # Get chapters related to the course
        chapters = Chapter.objects.filter(course=course)

        # chapters_with_lessons = {}
        
        # Create a dictionary to store chapters and their related lessons
        chapters_with_lessons = []
        chapters_with_lessons_and_quizzes = {}
        
        for chapter in chapters:
            # Get lessons related to the chapter
            lessons = Lesson.objects.filter(chapter=chapter)
            chapters_with_lessons.append((chapter, lessons))
            
            quizzes = Quiz.objects.filter(chapter=chapter)
            chapters_with_lessons_and_quizzes[chapter] = {
                'lessons': lessons,
                'quizzes': quizzes,
            }
            

            
        assignments = Assignment.objects.filter(course=self.kwargs['pk'])
        resources = Resource.objects.filter(course=self.kwargs['pk'])

        # Get the total number of lessons for the course
        total_lessons = Lesson.objects.filter(chapter__course=course).count()
        total_quizzes = course.total_quizzes()

        # Get the total number of completed lessons for the user in that course
        if self.request.user.is_authenticated:
            completed_lessons = CompletedLesson.objects.filter(user=self.request.user, lesson__chapter__course=course).count()
            completion_percentage = round((completed_lessons / total_lessons) * 100)
            print("Completed Lessons:", completed_lessons)

            # Access and print the lesson IDs directly
            completed_lessons1 = CompletedLesson.objects.filter(user=self.request.user, lesson__chapter__course=course)
            completed_lesson_ids = [completed_lesson.lesson.id for completed_lesson in completed_lessons1]
            print("Lesson IDs completed:", completed_lesson_ids)

            # can i get the chapter ids
            completed_chapter_ids = [completed_lesson.lesson.chapter.id for completed_lesson in completed_lessons1]
            print("Chapter IDs completed:", completed_chapter_ids)

                
            completed_quizzes = self.request.user.completed_quizzes(course)
          
             
            completion_percentage = round(((completed_lessons + completed_quizzes) / (total_lessons + total_quizzes)) * 100)
            print("Completion Percentage:", completion_percentage)
        else:
            completed_lessons = 0
            completed_quizzes = 0
            completion_percentage = 0
        
        if completion_percentage >= 100:
            #this is how i choose to update to the db that a user has completed a course
            # popup a congratulations window with instructions to generate/get your certificate
            # Check if the user has already completed the course
            if not CompletedCourse.objects.filter(user=self.request.user, course=course).exists():
                # Create a new CompletedCourse instance only if it doesn't exist
                completedcourse = CompletedCourse(user=self.request.user, course=course)
                completedcourse.save()
            

        context = super(CourseDetail, self).get_context_data(**kwargs)
        context['assignments'] = assignments
        context['resources'] = resources
        context['chapters_with_lessons'] = chapters_with_lessons 
        # return chapter name and lesson name
        context['chapters_with_lessons_and_quizzes'] = chapters_with_lessons_and_quizzes
        context['total_lessons'] = total_lessons
        context['completed_lessons'] = completed_lessons
        context['course.pk'] = course
        # context['course_id'] = course.pk
        context['completed_lesson_ids'] = completed_lesson_ids
        context['completed_lesson_ids_json'] = json.dumps(completed_lesson_ids)
        context['completed_quizzes'] = completed_quizzes
        context['completion_percentage'] = completion_percentage
        context['completed_chapter_ids'] = completed_chapter_ids
        return context


class ListCourse(generic.ListView):
    model = Course

class EnrollCourse(LoginRequiredMixin, generic.RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('courses:detail', kwargs={'pk':self.kwargs.get('pk')})
    
    def get(self, *args, **kwargs):
        course = get_object_or_404(Course, pk=self.kwargs.get('pk'))

        try:
            Enrollment.objects.create(student=self.request.user, course=course)
        except:
            messages.warning(self.request, 'You are already enrolled in the course.')
        else:
            messages.success(self.request, 'You are now enrolled in the course.')
        return super().get(self.request, *args, **kwargs)

class UnenrollCourse(LoginRequiredMixin, generic.RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('courses:detail', kwargs={'pk':self.kwargs.get('pk')})

    def get(self, *args, **kwargs):

        try:
            enrollment = Enrollment.objects.filter(
                student=self.request.user,
                course__pk=self.kwargs.get('pk')
            ).get()
        except Enrollment.DoesNotExist:
            messages.warning(self.request, 'You are not enrolled in this course.')
        else:
            enrollment.delete()
            messages.success(self.request, 'You have unenrolled from the course.')
        return super().get(self.request, *args, **kwargs)

class UpdateCourseView(LoginRequiredMixin, generic.UpdateView):
    model = Course
    form_class = UpdateCourseForm
    template_name = 'courses/update_course.html'
    success_url = '/all/'  

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Get the value of the 'pk' parameter from kwargs
        return get_object_or_404(Course, pk=pk)  # Retrieve the lesson object using the 'pk'




    
class UpdateChapterView(LoginRequiredMixin, generic.UpdateView):
    model = Chapter
    form = UpdateChapterForm
    template_name = 'courses/update_chapter.html'
    success_url = '/all/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Get the value of the 'pk' parameter from kwargs
        return get_object_or_404(Chapter, pk=pk)  # Retrieve the lesson object using the 'pk'
    
    def form_valid(self, form):
        if form.instance.course.teacher == self.request.user:
            return super().form_valid(form)
        else:
            form.add_error(None, "You don't have permission to edit this chapter.")
            return self.form_invalid(form)
        
class UpdateLessonView(LoginRequiredMixin, generic.UpdateView):
    model = Lesson
    form = UpdateLessonForm
    template_name = "courses/update_lesson.html"
    success_url = '/all/'
    
    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')  # Get the value of the 'pk' parameter from kwargs
        return get_object_or_404(Lesson, pk=pk)  # Retrieve the lesson object using the 'pk'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        if form.instance.chapter.course.teacher == self.request.user:
            return super().form_valid(form)
        else:
            form.add_error(None, "You don't have permission to edit this lesson.")
            return self.form_invalid(form)


def get_completed_lessons_count(request, course_id):
    if request.user.is_authenticated:
        course = get_object_or_404(Course, pk=course_id)
        completed_lessons_count = request.user.completed_lessons.filter(
            lesson__chapter__course=course
        ).count()
        # Access and print the lesson IDs directly
        completed_lessons1 = CompletedLesson.objects.filter(user=request.user, lesson__chapter__course=course)
        completed_lesson_ids = [completed_lesson.lesson.id for completed_lesson in completed_lessons1]
        print("Lesson IDss completed:", completed_lesson_ids)
        for i in completed_lesson_ids:
            # count
            print("Lesson: ", i)
        print(completed_lessons1.count())
        completed_lesson_count = completed_lessons1.count()
        context = {
            'completed_lessons_count': completed_lesson_count,
            'completed_lesson_ids': completed_lesson_ids,
        }
        print("completed_lessons_count:", completed_lesson_count)
        return JsonResponse(context)
    else:
        return JsonResponse({'message': 'Invalid request method.'}, status=400)
# class CompletedLessonCountView(View):
#     def get(self, request, *args, **kwargs):
#         course_pk = self.kwargs['pk']  # Access the 'pk' parameter from the URL
#         # Your logic to calculate completed lesson count
#         course = get_object_or_404(Course, pk=course_pk)
#         completed_lessons_count = request.user.completed_lessons.filter(
#             lesson__chapter__course=course
#         ).count()
#         data = {'completed_lessons_count': completed_lessons_count}
#         return JsonResponse(data)
        

def mark_lesson_as_complete(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        lesson_id = data.get('lesson_id')
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON data.'}, status=400)

    if not lesson_id:
        return JsonResponse({'message': 'Missing lesson ID.'}, status=400)

    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'message': 'Lesson not found.'}, status=404)

    user = request.user

    # Check if the lesson is already marked as complete for the user
    if CompletedLesson.objects.filter(user=user, lesson=lesson).exists():
        return JsonResponse({'message': 'Lesson is already marked as complete.'}, status=200)

    # Mark the lesson as complete for the user
    completed_lesson = CompletedLesson(user=user, lesson=lesson)
    completed_lesson.save()

    # Calculate the completion percentage for the course
    course = lesson.chapter.course
    total_lessons = Lesson.objects.filter(chapter__course=course).count()
    total_quizzes = course.total_quizzes()
    completed_lessons = user.completed_lessons.filter(lesson__chapter__course=course).count()
    completed_quizzes = user.completed_quizzes(course)
    completion_percentage = round(((completed_lessons + completed_quizzes) / (total_lessons + total_quizzes)) * 100)
    print("completed quizes: ", completed_quizzes)

    # Update the progress bar or any other elements as needed

    return JsonResponse({'message': 'Lesson marked as complete successfully.', 'completed_lessons_count': completed_lessons, 'completion_percentage': completion_percentage}, status=200)

