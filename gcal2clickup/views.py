from django.shortcuts import render

def google_verification(request):
	return render(request, 'staticfiles/google_verification.html', {})
