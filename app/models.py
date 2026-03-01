from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = CloudinaryField('image', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    address_line = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=50, default='India')
    phone_number = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # If this address is set to default, unset all other default addresses for this user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.city} ({'Default' if self.is_default else 'Secondary'})"

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = CloudinaryField('image', blank=True, null=True)
    # Comma-separated tags, e.g. "denim, jacket, upcycle"
    tags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)

    def __str__(self):
        return f"{self.author.username}: {self.title}"

    def like_count(self):
        return self.likes.count()

    def get_tags_list(self):
        # Returns tags as a Python list, stripping whitespace from each
        return [t.strip() for t in self.tags.split(',') if t.strip()]

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on '{self.post.title}'"

class Donation(models.Model):
    # Two ways to donate: drop it off yourself, or request a pickup
    DONATION_TYPE_CHOICES = [
        ('self_drop', 'Self Drop-off'),
        ('pickup', 'Schedule Pickup'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('picked_up', 'Picked Up'),
        ('received', 'Received at Center'),
        ('completed', 'Completed'),
    ]

    # Coins per garment based on condition
    COIN_REWARDS = {
        'Like New': 20,
        'Good': 15,
        'Fair': 10,
        'Needs Repair': 5,
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    donation_type = models.CharField(max_length=20, choices=DONATION_TYPE_CHOICES)
    clothing_type = models.CharField(max_length=100, help_text="e.g. T-Shirt, Jeans, Jacket")
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=50, help_text="e.g. Good, Fair, Needs Repair")
    description = models.TextField(blank=True, help_text="Any extra details about the clothes")
    image = CloudinaryField('image', blank=True, null=True)

    # Pickup-specific fields (only used when donation_type == 'pickup')
    pickup_address = models.TextField(blank=True, null=True)
    pickup_date = models.DateField(blank=True, null=True)
    pickup_time_slot = models.CharField(max_length=50, blank=True, null=True)

    # Reward coins for donating
    coins_earned = models.PositiveIntegerField(default=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.clothing_type} ({self.get_donation_type_display()})"

    def calculate_coins(self):
        # Look up the per-item reward from the condition, default to 5 if unknown
        per_item = self.COIN_REWARDS.get(self.condition, 5)
        return per_item * self.quantity
