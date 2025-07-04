from django.db import models  # Import Django's model base class and field types
from django.utils import timezone  # Import timezone utilities for default timestamps

# --------------------------------------------------------------------------
# Model for a poll question (used in the poll/voting system)
class Question(models.Model):  # Inherit from Model to create a database table
    text = models.CharField(max_length=255)  
    # CharField: stores string data up to 255 characters
    # This field stores the actual question text like "What's your favorite programming language?"
    # max_length=255 means maximum 255 characters allowed
    
    pub_date = models.DateTimeField(default=timezone.now)  
    # DateTimeField: stores date and time
    # default=timezone.now means when a new Question is created, it automatically gets current timestamp
    # timezone.now is timezone-aware (better than datetime.now)
    # Used for ordering questions chronologically

    # Up to 4 possible choices (answers) for the question, can be empty/blank if not used
    choice1 = models.CharField(max_length=255, blank=True)
    # blank=True means this field is optional in forms (can be left empty)
    # This allows questions with fewer than 4 choices
    
    choice2 = models.CharField(max_length=255, blank=True)
    choice3 = models.CharField(max_length=255, blank=True)
    choice4 = models.CharField(max_length=255, blank=True)
    # Each choice can hold up to 255 characters of text
    # Example: choice1="Python", choice2="JavaScript", choice3="Java", choice4="C++"

    def __str__(self):  # Special method called when converting object to string
        return self.text  # Returns question text for admin interface and debugging
        # Example: print(question) would print "What's your favorite programming language?"

# --------------------------------------------------------------------------
# Model to count votes for a question's specific choice.
class VotingCount(models.Model):
    question = models.ForeignKey(
        Question,  # References the Question model
        related_name='voting_counts',  # Allows question.voting_counts.all() to get all vote counts
        on_delete=models.CASCADE  # If question is deleted, delete all its vote counts too
    )  
    # ForeignKey creates a many-to-one relationship
    # Many VotingCount records can belong to one Question

    choice_index = models.PositiveIntegerField(default=0)
    # PositiveIntegerField: stores non-negative integers (0, 1, 2, 3...)
    # Represents which choice this count is for:
    # 0 = choice1, 1 = choice2, 2 = choice3, 3 = choice4
    # default=0 means if not specified, it's for choice1
    
    count = models.IntegerField(default=0)  
    # IntegerField: stores positive or negative integers
    # Stores the actual number of votes
    # default=0 means new records start with 0 votes

    # Returns the actual text for the choice at the current index
    def choice_text(self):  # Instance method to get the choice text
        choices = [  # Create list of all choices from the related question
            self.question.choice1,  # Index 0
            self.question.choice2,  # Index 1
            self.question.choice3,  # Index 2
            self.question.choice4,  # Index 3
        ]
        if 0 <= self.choice_index < len(choices):  # Validate index is within bounds
            return choices[self.choice_index]  # Return the choice at this index
            # Example: if choice_index=1, returns self.question.choice2
        return "(Unknown choice)"  # Fallback for invalid indices

    def __str__(self):
        return f"Votes for '{self.question.text}' choice {int(self.choice_index) + 1}: {self.count}"
        # Example output: "Votes for 'What's your favorite color?' choice 2: 45"
        # Note: int(self.choice_index) + 1 converts 0-based index to 1-based for display

# --------------------------------------------------------------------------
# Model for "voter verification" (used in the election/voting for candidates)
class Verification(models.Model):
    phone_or_adhar = models.CharField(max_length=20, unique=True)
    # CharField with max 20 characters for phone number or Aadhaar number
    # unique=True ensures no duplicate entries - each phone/Aadhaar can only register once
    # This prevents multiple accounts with same ID
    
    password = models.CharField(max_length=128)
    # Stores password (WARNING: appears to be plain text - should use hashing in production!)
    # max_length=128 accommodates hashed passwords if upgraded to use hashing

    used = models.BooleanField(default=False)
    # BooleanField: stores True/False values
    # default=False means new verifications start as unused
    # Set to True after voter casts their vote
    # Prevents double voting with same credentials

    def __str__(self):
        return self.phone_or_adhar  # Display phone/Aadhaar in admin

# --------------------------------------------------------------------------
# Represents a single election candidate ("member") people can vote for
class Members(models.Model):  # Note: Should be singular "Member" by Django convention
    name = models.CharField(max_length=100)
    # Candidate's full name, up to 100 characters
    # Required field (no blank=True, so must be provided)
    
    photo = models.ImageField(upload_to='member_photos/')
    # ImageField: specialized field for uploading images
    # upload_to='member_photos/' means files go to MEDIA_ROOT/member_photos/
    # Requires Pillow library to be installed
    # Files are renamed to avoid conflicts (adds random suffix if needed)

    def __str__(self):
        return self.name  # Shows candidate name in admin and when printed

# --------------------------------------------------------------------------
# Stores the election vote count for each member
class ElectCount(models.Model):
    member = models.ForeignKey(
        Members,  # References the Members model
        on_delete=models.CASCADE,  # If member deleted, delete their vote count
        related_name='elect_counts'  # Allows member.elect_counts.all()
    )
    # Creates relationship: each ElectCount belongs to one Member
    # But a Member can have multiple ElectCount records (though typically just one)

    count = models.IntegerField(default=0)
    # The actual vote tally for this member
    # Incremented each time someone votes for this member
    # default=0 means candidates start with zero votes

    def __str__(self):
        return f"Votes for {self.member.name}: {self.count}"
        # Example: "Votes for John Doe: 150"
