from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib import messages
from .models import UserProfile, Address

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
