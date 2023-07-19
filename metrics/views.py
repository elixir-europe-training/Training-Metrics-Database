from django.shortcuts import render

# Create your views here.
def test(request):
    return render(request, 'metrics/index.html')