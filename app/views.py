from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile, Address, Post, Comment, Donation

# -- Public views (no login needed) --

def landing(request):
    # If user is already logged in, just send them to the dashboard
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing.html')

def login_view(request):
    # If already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Django's default User model uses 'username' for auth,
        # so we need to find the user by email first
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email.')
            return render(request, 'login.html')

        # Now authenticate with the username we found
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid password. Please try again.')
            return render(request, 'login.html')

    return render(request, 'login.html')

def signup_view(request):
    # If already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if a user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'signup.html')

        # Create the user - we use email as the username too for simplicity
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Auto-login after signup so the user goes straight to the app
        login(request, user)
        return redirect('home')

    return render(request, 'signup.html')

def logout_view(request):
    logout(request)
    return redirect('landing')


# -- Protected views (login required) --

@login_required
def home(request):
    context = {
        'coins': 150,
        'notifications': 3,
    }
    return render(request, 'home.html', context)

@login_required
def settings_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update Base User fields
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Update UserProfile fields
        profile.phone_number = request.POST.get('phone_number', '')
        profile.bio = request.POST.get('bio', '')
        
        # Handle Profile Picture Uploads
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('settings')
        
    # Get user addresses ordered with default first
    addresses = request.user.addresses.all().order_by('-is_default', 'id')
        
    return render(request, 'settings.html', {'profile': profile, 'addresses': addresses})

@login_required
def add_address(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address_line = request.POST.get('address_line')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country', 'India')
        phone_number = request.POST.get('phone_number')
        
        # Check if this should be default (if it's the first address, or checkbox checked)
        is_default = request.POST.get('is_default') == 'on' or not request.user.addresses.exists()

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            address_line=address_line,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            phone_number=phone_number,
            is_default=is_default
        )
        messages.success(request, 'Address added successfully!')
        
    return redirect('settings')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.full_name = request.POST.get('full_name')
        address.address_line = request.POST.get('address_line')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        address.country = request.POST.get('country', 'India')
        address.phone_number = request.POST.get('phone_number')
        
        if request.POST.get('is_default') == 'on':
            address.is_default = True
            
        address.save()
        messages.success(request, 'Address updated successfully!')
        
    return redirect('settings')

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # If we are deleting the default address and there are others, we should probably 
    # not auto-assign a new default here for simplicity, or we can. 
    # Let's just delete it and let the user set a new default.
    address.delete()
    messages.success(request, 'Address removed.')
    return redirect('settings')

@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Triggering the save method will automatically unset the others
    address.is_default = True
    address.save()
    
    messages.success(request, 'Default address updated!')
    return redirect('settings')


# -- Community Feed Views --

@login_required
def community_view(request):
    # Fetch all posts, newest first, with related data pre-fetched to reduce DB queries
    posts = Post.objects.all().order_by('-created_at').select_related('author', 'author__profile').prefetch_related('comments', 'likes')
    return render(request, 'community.html', {'posts': posts})

@login_required
def create_post(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        tags = request.POST.get('tags', '').strip()

        if not title or not description:
            messages.error(request, 'Title and description are required.')
            return redirect('community')

        post = Post(
            author=request.user,
            title=title,
            description=description,
            tags=tags,
        )

        # Only attach an image if one was uploaded
        if 'image' in request.FILES:
            post.image = request.FILES['image']

        post.save()
        messages.success(request, 'Post shared with the community!')
    return redirect('community')

@login_required
def like_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        # Toggle: if already liked, remove the like, otherwise add it
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True
        
        # Return JSON for fetch/AJAX calls so the page doesn't reload
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'liked': liked, 'count': post.like_count()})
    return redirect('community')

@login_required
def add_comment(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        body = request.POST.get('body', '').strip()
        if body:
            comment = Comment.objects.create(post=post, author=request.user, body=body)
            
            # Return JSON for AJAX calls
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                author_name = request.user.get_full_name() or request.user.username
                initials = ((request.user.first_name[:1] + request.user.last_name[:1]).upper()) or 'A'
                # Safely get avatar — user may not have a profile record yet
                try:
                    avatar_url = request.user.profile.profile_picture.url if request.user.profile.profile_picture else None
                except Exception:
                    avatar_url = None
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'delete_url': f'/community/comment/{comment.id}/delete/',
                        'author': author_name,
                        'initials': initials,
                        'avatar_url': avatar_url,
                        'body': comment.body,
                    }
                })
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False})
    return redirect('community')

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
    return redirect('community')

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)

    if request.method == 'GET':
        # Return current post data as JSON so the modal can pre-fill the form
        return JsonResponse({
            'id': post.id,
            'title': post.title,
            'description': post.description,
            'tags': post.tags,
        })

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        tags = request.POST.get('tags', '').strip()

        if not title or not description:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Title and description are required.'})
            return redirect('community')

        post.title = title
        post.description = description
        post.tags = tags
        post.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, 'Post updated!')
    return redirect('community')

@login_required
def delete_comment(request, comment_id):
    # Only the comment's author can delete it
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    if request.method == 'POST':
        comment.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
    return redirect('community')


# -- Donation Views --

@login_required
def donation_view(request):
    # Show all donations by the logged-in user, newest first
    donations = request.user.donations.all().order_by('-created_at')
    # Get user addresses for the pickup form dropdown
    addresses = request.user.addresses.all().order_by('-is_default', 'id')
    return render(request, 'donation.html', {'donations': donations, 'addresses': addresses})

@login_required
def create_donation(request):
    if request.method == 'POST':
        donation_type = request.POST.get('donation_type')
        clothing_type = request.POST.get('clothing_type', '').strip()
        quantity = request.POST.get('quantity', 1)
        condition = request.POST.get('condition', '').strip()
        description = request.POST.get('description', '').strip()

        if not clothing_type or not condition:
            messages.error(request, 'Clothing type and condition are required.')
            return redirect('donation')

        donation = Donation(
            user=request.user,
            donation_type=donation_type,
            clothing_type=clothing_type,
            quantity=int(quantity),
            condition=condition,
            description=description,
        )

        # Attach image if uploaded
        if 'image' in request.FILES:
            donation.image = request.FILES['image']

        # If pickup, grab the address and scheduling details
        if donation_type == 'pickup':
            donation.pickup_address = request.POST.get('pickup_address', '')
            donation.pickup_date = request.POST.get('pickup_date') or None
            donation.pickup_time_slot = request.POST.get('pickup_time_slot', '')

        # Calculate coins based on condition and quantity before saving
        donation.coins_earned = donation.calculate_coins()
        donation.save()
        messages.success(request, f'Donation submitted! You earned {donation.coins_earned} coins.')

    return redirect('donation')

@login_required
def cancel_donation(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id, user=request.user)
    # Only allow cancelling if it's still pending
    if donation.status == 'pending':
        donation.delete()
        messages.success(request, 'Donation cancelled.')
    else:
        messages.error(request, 'This donation can no longer be cancelled.')
    return redirect('donation')
