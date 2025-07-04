# Django built-in and custom imports
from django.shortcuts import render, get_object_or_404, redirect  # Common Django shortcuts for rendering templates and handling 404s
from .models import Question, VotingCount, Verification, Members, ElectCount  # Import all models from current app
from .forms import QuestionsForm  # Import form for creating/editing questions
from django.urls import reverse  # For reversing URL patterns (though not used in this code)
from django.http import HttpResponseRedirect  # For HTTP redirects (though redirect is used instead)
from django.contrib.admin.views.decorators import staff_member_required  # Decorator to restrict view to staff users only
from django.contrib.auth.forms import UserCreationForm  # Django's built-in form for user registration
from django.contrib.auth import login as auth_login  # For logging users in (though not used in this code)
from django.contrib.auth.decorators import login_required  # Decorator to restrict views to authenticated users
from django.db.models import Sum  # For aggregating sum of database fields

# ------------------------------------------------------------------
# Show a list of all questions in order of publication date. Only available to logged-in users.
@login_required  # This decorator ensures only logged-in users can access this view
def question_list(request):  # request contains HTTP request data
    questions = Question.objects.all().order_by('pub_date')  # Query database for all Question objects, sort by publication date (oldest first)
    return render(request, 'polls/question_list.html', {'questions': questions})  # Render template with questions data

# ------------------------------------------------------------------
# Show details for a specific question (with voting stats), only for logged in users.
@login_required  # Requires user authentication
def question_detail(request, pk):  # pk is the primary key of the question passed from URL
    question = get_object_or_404(Question, pk=pk)  # Get question by primary key or return 404 if not found
    choices = get_choices(question)  # Call helper function to get list of choices [choice1, choice2, choice3, choice4]
    voted = request.session.get(f'voted_{pk}', None)  # Check if user already voted (stored in session as 'voted_123' where 123 is question pk)

    # Gather vote counts for each choice
    vote_counts = []  # Initialize empty list to store vote counts
    total_votes = 0  # Initialize total vote counter
    for idx, choice in enumerate(choices):  # Loop through choices with index (0,1,2,3)
        if choice:  # If choice text exists (not empty)
            count = VotingCount.objects.filter(question=question, choice_index=idx).first()  # Find VotingCount record for this question and choice
            count_val = count.count if count else 0  # Get count value, or 0 if no record exists
            vote_counts.append(count_val)  # Add to vote counts list
            total_votes += count_val  # Add to running total
        else:  # If choice is empty
            vote_counts.append(0)  # Add 0 to maintain list alignment

    # Find which choice currently leads in votes (the index)
    leading_idx = None  # Initialize as None
    if total_votes > 0:  # Only calculate if there are votes
        max_votes = max(vote_counts)  # Find highest vote count
        leading_idx = vote_counts.index(max_votes) if max_votes > 0 else None  # Get index of leading choice

    # Compute percentage of total votes per choice
    percentages = []  # Initialize percentages list
    for count in vote_counts:  # Loop through each vote count
        if total_votes > 0:  # Avoid division by zero
            percentages.append(int(round(count * 100 / total_votes)))  # Calculate percentage and round to integer
        else:
            percentages.append(0)  # If no votes, percentage is 0

    results = zip(choices, vote_counts, percentages)  # Combine choices, counts, and percentages into tuples

    # For navigation: find if there's a next question (by date)
    next_q = Question.objects.filter(pub_date__gt=question.pub_date).order_by('pub_date').first()  # Get next question after current one by date
    next_question_pk = next_q.pk if next_q else None  # Get primary key if exists, else None
    is_last_question = next_q is None  # Boolean flag for last question

    # Render template with all voting and results info
    return render(request, 'polls/question_detail.html', {  # Render template with context data
        'question': question,  # Current question object
        'choices': choices,  # List of choice texts
        'voted': voted,  # Index of user's vote if they voted
        'vote_counts': vote_counts,  # List of vote counts per choice
        'total_votes': total_votes,  # Sum of all votes
        'leading_idx': leading_idx,  # Index of leading choice
        'percentages': percentages,  # List of percentages per choice
        'results': results,  # Zipped choices, counts, percentages
        'next_question_pk': next_question_pk,  # PK of next question for navigation
        'is_last_question': is_last_question,  # Boolean if this is the last question
    })

# ------------------------------------------------------------------
# Handle voting for a question (POST only, must be logged in). Updates vote count and sets session.
@login_required  # Requires authentication
def vote(request, pk):  # pk is question primary key
    question = get_object_or_404(Question, pk=pk)  # Get question or 404
    choices = get_choices(question)  # Get list of choices
    if request.method == 'POST':  # Only process POST requests (form submissions)
        choice_index = request.POST.get('choice')  # Get selected choice index from form data
        # User must select a valid option
        if choice_index is not None and choice_index.isdigit():  # Check if choice exists and is a number
            idx = int(choice_index)  # Convert to integer
            if 0 <= idx < len(choices) and choices[idx]:  # Validate index is in range and choice exists
                # Increment/Create vote record for this choice
                voting_count, created = VotingCount.objects.get_or_create(question=question, choice_index=idx)  # Get existing or create new VotingCount
                voting_count.count += 1  # Increment the vote count
                voting_count.save()  # Save to database
                # Remember that this user voted (session-based, not global)
                request.session[f'voted_{pk}'] = idx  # Store in session that user voted for this choice
                return redirect('question_detail', pk=pk)  # Redirect back to question detail page

        # Handle error if no/invalid selection (re-display page w/ data and error)
        error = 'Please select a choice.'  # Error message
        vote_counts = []  # Recalculate vote counts for display
        total_votes = 0
        for i, choice in enumerate(choices):  # Loop through choices
            if choice:  # If choice exists
                count = VotingCount.objects.filter(question=question, choice_index=i).first()  # Get vote count
                count_val = count.count if count else 0
                vote_counts.append(count_val)
                total_votes += count_val
            else:
                vote_counts.append(0)
        leading_idx = None
        if total_votes > 0:  # Calculate leading choice
            max_votes = max(vote_counts)
            leading_idx = vote_counts.index(max_votes) if max_votes > 0 else None
        percentages = []  # Calculate percentages
        for count in vote_counts:
            if total_votes > 0:
                percentages.append(int(round(count * 100 / total_votes)))
            else:
                percentages.append(0)
        results = zip(choices, vote_counts, percentages)  # Zip results
        return render(request, 'polls/question_detail.html', {  # Render with error
            'question': question,
            'choices': choices,
            'error': error,  # Include error message
            'voted': None,  # User hasn't successfully voted
            'vote_counts': vote_counts,
            'total_votes': total_votes,
            'leading_idx': leading_idx,
            'percentages': percentages,
            'results': results,
        })
    # GET: redirect to detail page (no direct GET voting)
    return redirect('question_detail', pk=pk)  # If GET request, redirect to detail page

# ------------------------------------------------------------------
# Add a new question (staff-only)
@staff_member_required  # Only staff members can access
def question_create(request):
    if request.method == 'POST':  # If form submitted
        form = QuestionsForm(request.POST)  # Create form with POST data
        if form.is_valid():  # Validate form data
            question = form.save()  # Save new question to database
            return redirect('question_detail', pk=question.pk)  # Redirect to new question's detail page
    else:  # GET request
        form = QuestionsForm()  # Create empty form
    return render(request, 'polls/question_form.html', {'form': form})  # Render form template

# ------------------------------------------------------------------
# Edit a question (no access control here; consider adding one)
def question_update(request, pk):  # pk is question primary key
    question = get_object_or_404(Question, pk=pk)  # Get question or 404
    if request.method == 'POST':  # If form submitted
        form = QuestionsForm(request.POST, instance=question)  # Create form with POST data, bound to existing question
        if form.is_valid():  # Validate
            form.save()  # Update question in database
            return redirect('question_detail', pk=question.pk)  # Redirect to updated question
    else:  # GET request
        form = QuestionsForm(instance=question)  # Create form pre-filled with question data
    return render(request, 'polls/question_form.html', {'form': form, 'question': question})  # Render form

# ------------------------------------------------------------------
# Delete a question (with confirm page)
def question_delete(request, pk):  # pk is question primary key
    question = get_object_or_404(Question, pk=pk)  # Get question or 404
    if request.method == 'POST':  # If deletion confirmed
        question.delete()  # Delete from database
        return redirect('question_list')  # Redirect to question list
    return render(request, 'polls/question_confirm_delete.html', {'question': question})  # Show confirmation page

# ------------------------------------------------------------------
# Helper: Return all choices for a question as a list
def get_choices(question):  # Helper function takes question object
    return [  # Return list of choices
        question.choice1,  # First choice
        question.choice2,  # Second choice
        question.choice3,  # Third choice
        question.choice4,  # Fourth choice
    ]

# ------------------------------------------------------------------
# Register new user
def signup(request):
    if request.method == 'POST':  # If form submitted
        form = UserCreationForm(request.POST)  # Create form with POST data
        if form.is_valid():  # Validate (username unique, passwords match, etc.)
            user = form.save()  # Create new user in database
            return redirect('login')  # Redirect to login page
    else:  # GET request
        form = UserCreationForm()  # Create empty registration form
    return render(request, 'registration/signup.html', {'form': form})  # Render signup template

# ------------------------------------------------------------------
# Simple homepage view
def home(request):
    return render(request, 'polls/home.html')  # Just render the home template

# ------------------------------------------------------------------
# Handle verification login by phone or adhar number, and one-time use password
def verification_view(request):
    error = None  # Initialize error message as None
    if request.method == 'POST':  # If form submitted
        phone_or_adhar = request.POST.get('phoneno')  # Get phone/adhar from form (field named 'phoneno')
        password = request.POST.get('password')  # Get password from form
        try:
            verification = Verification.objects.get(phone_or_adhar=phone_or_adhar, password=password)  # Try to find matching verification record
            if verification.used:  # Check if already used
                error = "You already voted. don't try to cheat"  # Set error message
            else:  # If not used yet
                verification.used = True  # Mark as used
                verification.save()  # Save to database
                return redirect('member_list')  # Redirect to member voting page
        except Verification.DoesNotExist:  # If no matching record found
            error = "Invalid credentials. Please try again."  # Set error message
    return render(request, 'registration/verification.html', {'error': error})  # Render verification page with error if any

# ------------------------------------------------------------------
# List all candidates/members, allow voting for one
def member_list(request):
    members = Members.objects.all().order_by('-elect_counts')  # Get all members, order by related elect_counts (though this may not work as intended)
    if request.method == 'POST':  # If vote submitted
        member_id = request.POST.get('member_id')  # Get selected member ID from form
        if member_id:  # If member selected
            member = Members.objects.get(id=member_id)  # Get member object
            elect_count, created = ElectCount.objects.get_or_create(member=member)  # Get or create vote count for member
            elect_count.count += 1  # Increment vote count
            elect_count.save()  # Save to database
            return render(request, 'polls/vote_result.html', {'member': member})  # Show vote confirmation
    return render(request, 
