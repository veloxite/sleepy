"""Opt-in live Groq checks. Only generated test content is sent."""
from PIL import Image, ImageDraw, ImageFont
from agent_core import Agent, encode_image
from api_connections import fetch_models

def run():
    agent=Agent()
    config={'base_url':'https://api.groq.com/openai/v1','api_key':agent.client.api_key}
    models=fetch_models(config)
    assert agent.text_model in models and agent.vision_model in models
    print('PASS: model discovery; configured chat and vision models are available')
    picture=Image.new('RGB',(800,300),'white')
    draw=ImageDraw.Draw(picture)
    try:
        font=ImageFont.truetype('arial.ttf',40);small=ImageFont.truetype('arial.ttf',22)
    except OSError:
        font=ImageFont.load_default(size=40);small=ImageFont.load_default(size=22)
    draw.text((40,40),'Problem 3.14. Evaluate:',fill='black',font=font)
    draw.text((40,125),'log',fill='black',font=font)
    draw.text((100,152),'2',fill='black',font=small)
    draw.text((122,125),'(10)',fill='black',font=font)
    answer=agent.reply('Transcribe the displayed problem, then solve it to three decimal places.',encode_image(picture))
    assert '3.32' in answer, 'The synthetic logarithm problem was not read correctly.'
    print('PASS: synthetic log-base-2 problem was solved as approximately 3.322')

if __name__=='__main__':run()
