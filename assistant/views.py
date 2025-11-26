from rest_framework.views import APIView
from rest_framework.response import Response
from .services.ai_engine import improve_text


from django.shortcuts import render, redirect

class ImproveAPIView(APIView):
    def post(self, request):
        text = request.data.get("text")
        task = request.data.get("task", "grammar")

        if not text:
            return Response({"error": "Text is required"}, status=400)

        result = improve_text(text, task)
        return Response({"result": result})




# for the html

def improve_page(request):
    return render(request, "index.html")
