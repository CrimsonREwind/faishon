import os
import re
import json
import base64
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def generate_ideas(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    try:
        # Get the files from the request (front, back, closeup)
        front_file = request.FILES.get('front')
        back_file = request.FILES.get('back')
        closeup_file = request.FILES.get('closeup')

        if not (front_file and back_file and closeup_file):
            return JsonResponse({'error': 'Missing one or more required images (front, back, closeup).'}, status=400)

        # Convert images to base64 strings
        def file_to_b64(f):
            return base64.b64encode(f.read()).decode('utf-8')

        b64_front = file_to_b64(front_file)
        b64_back = file_to_b64(back_file)
        b64_closeup = file_to_b64(closeup_file)

        # Nvidia NIM API setup
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        api_key = os.environ.get("NVIDIA_API_KEY", "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")
        
        if not api_key:
            return JsonResponse({'error': 'Nvidia API Key is missing on the server.'}, status=500)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }

        # Prompt engineering to get structured JSON out of the model
        system_prompt = """
        You are a sustainable fashion AI expert.
        Analyze the provided images of an old garment (Front, Back, Closeup).
        Extract technical details about the garment and propose exactly 3 creative upcycle concepts for it (ideas only, no detailed instructions).
        
        You MUST respond ONLY with valid JSON in the exact format shown below, with no markdown code blocks wrapping it:
        {
          "garment_type": "T-Shirt",
          "subcategory": "Graphic Tee",
          "primary_color": "Blue",
          "secondary_colors": ["White", "Red"],
          "fabric_type": "Cotton blend",
          "pattern": "Solid with print",
          "fit": "Regular",
          "sleeve_length": "Short",
          "seasonality": ["Summer", "Spring"],
          "estimated_reusability_score": 85,
          "confidence": 0.95,
          "concepts": [
            {
              "title": "Patchwork Tote Bag",
              "difficulty": "Easy",
              "description": "Turn the sturdy body panels into an everyday reusable tote with contrasting pockets."
            },
            {
              "title": "Cropped Layering Vest",
              "difficulty": "Medium",
              "description": "Cut off sleeves and hem, distress the edges for a modern vintage look."
            },
            {
              "title": "Bucket Hat",
              "difficulty": "Hard",
              "description": "Re-pattern the fabric into a stylish, structured bucket hat for summer."
            }
          ]
        }
        Limit 'difficulty' to: Easy, Medium, Hard.
        """

        content_list = [
            {"type": "text", "text": system_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_front}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_back}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_closeup}"}},
            {"type": "text", "text": "Based on these 3 images (Front, Back, Closeup details), generate the technical garment analysis and the 3 concepts in the requested JSON format."}
        ]

        payload = {
            "model": "qwen/qwen3.5-397b-a17b",
            "messages": [
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            "max_tokens": 8192,
            "temperature": 0.60,
            "top_p": 0.95,
            "top_k": 20,
            "presence_penalty": 0,
            "repetition_penalty": 1,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False}
        }

        # Make the request to Nvidia NIM
        response = requests.post(invoke_url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # The AI response is typically inside choices[0].message.content
        ai_message = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Extract the JSON object using regex to ignore any conversational filler
        match = re.search(r'\{.*\}', ai_message, re.DOTALL)
        if not match:
            return JsonResponse({'error': 'AI response did not contain a valid JSON object.', 'raw': ai_message}, status=500)
            
        clean_json = match.group(0).strip()

        # Parse the JSON string to an actual Python object
        analysis_result = json.loads(clean_json)

        return JsonResponse(analysis_result, status=200)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Failed to communicate with AI API: {str(e)}'}, status=502)
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Failed to parse AI response as JSON: {str(e)} | Raw: {ai_message}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@csrf_exempt
def generate_instructions(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    try:
        # We expect a JSON body with the chosen concept details
        body = json.loads(request.body)
        concept_title = body.get('title')
        concept_desc = body.get('description')
        garment_info = body.get('garment_info', {}) # The technical analysis from phase 1

        if not concept_title or not concept_desc:
            return JsonResponse({'error': 'Missing concept title or description.'}, status=400)

        # Nvidia NIM API setup
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        api_key = os.environ.get("NVIDIA_API_KEY", "")
        
        if not api_key:
            return JsonResponse({'error': 'Nvidia API Key is missing on the server.'}, status=500)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }

        # Prompt for detailed instructions
        system_prompt = f"""
        You are a master tailor and sustainable fashion instructor.
        The user has an old garment with these details: {json.dumps(garment_info)}
        They have chosen to upcycle it into this concept: "{concept_title}" ({concept_desc}).
        
        Generate a detailed, step-by-step tutorial on how to accomplish this.
        
        You MUST respond ONLY with valid JSON in the exact format shown below, with no markdown code blocks wrapping it:
        {{
          "tools_needed": ["Fabric scissors", "Pins", "Sewing machine", "Thread matching {garment_info.get('primary_color', 'the fabric')}"],
          "estimated_time_minutes": 120,
          "instructions": [
            "Lay the {garment_info.get('garment_type', 'garment')} flat on a clean table and smooth out any wrinkles.",
            "Using chalk, draw a cutting line 2 inches below the armpits.",
            ...
          ],
          "pro_tip": "If the fabric is prone to fraying, sew a zig-zag stitch along the raw edge before continuing."
        }}
        """

        payload = {
            "model": "qwen/qwen3.5-397b-a17b",
            "messages": [
                {
                    "role": "user",
                    "content": system_prompt
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.40,  # Lower temp for more procedural/instructional text
            "top_p": 0.95,
            "presence_penalty": 0,
            "repetition_penalty": 1,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False}
        }

        # Make the request to Nvidia NIM
        response = requests.post(invoke_url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        ai_message = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Extract the JSON object using regex
        match = re.search(r'\{.*\}', ai_message, re.DOTALL)
        if not match:
            return JsonResponse({'error': 'AI response did not contain a valid JSON object.', 'raw': ai_message}, status=500)
            
        clean_json = match.group(0).strip()
        instructions_result = json.loads(clean_json)

        return JsonResponse(instructions_result, status=200)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Failed to communicate with AI API: {str(e)}'}, status=502)
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Failed to parse request JSON or AI response JSON: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
