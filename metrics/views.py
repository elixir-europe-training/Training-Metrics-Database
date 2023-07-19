from django.shortcuts import render

# Create your views here.
def test(request):
    name='eleni'
    return render(request, 'metrics/index.html', context={'name':name})