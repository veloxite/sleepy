"""Public image search with source credits; no model-invented image URLs."""
import base64
import html
import io
import json
import re
import urllib.request
from urllib.parse import urlencode,urlsplit
from PIL import Image

def search_images(query):
    params={'action':'query','format':'json','generator':'search','gsrsearch':str(query)[:200],
            'gsrnamespace':6,'gsrlimit':8,'prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':500}
    request=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+urlencode(params),headers={'User-Agent':'SleepyDesktop/0.2 (personal educational image search)'})
    with urllib.request.urlopen(request,timeout=20) as response:data=json.load(response)
    images=[]
    for page in data.get('query',{}).get('pages',{}).values():
        info=(page.get('imageinfo') or [{}])[0];url=info.get('thumburl','')
        if urlsplit(url).hostname!='upload.wikimedia.org':continue
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'SleepyDesktop/0.2'})
            with urllib.request.urlopen(request,timeout=15) as response:
                if urlsplit(response.url).hostname!='upload.wikimedia.org':continue
                payload=response.read(2_000_001)
            if len(payload)>2_000_000:continue
            with Image.open(io.BytesIO(payload)) as picture:
                picture.thumbnail((500,400));output=io.BytesIO();picture.convert('RGB').save(output,format='JPEG',quality=78)
            meta=info.get('extmetadata',{})
            def plain(key):return html.unescape(re.sub('<[^>]+>','',meta.get(key,{}).get('value','')))[:250]
            images.append({'title':page.get('title','Image').removeprefix('File:'),'source':info.get('descriptionurl',''),
                           'credit':plain('Artist'),'license':plain('LicenseShortName'),
                           'image':'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()})
        except Exception:continue
        if len(images)==3:break
    if not images:raise ValueError('No suitable web images were found. Try a more specific topic.')
    return images

def youtube_results(query):
    import yt_dlp
    class Quiet:
        def debug(self,*args):pass
        def warning(self,*args):pass
        def error(self,*args):pass
    with yt_dlp.YoutubeDL({'quiet':True,'logger':Quiet(),'extract_flat':True,'skip_download':True,'socket_timeout':15,'retries':0}) as ydl:
        result=ydl.extract_info('ytsearch5:'+query[:200],download=False)
    videos=[]
    for item in (result or {}).get('entries',[]):
        vid=item.get('id','')
        if re.fullmatch(r'[\w-]{11}',vid):videos.append({'title':item.get('title','YouTube video'),'author':item.get('channel') or item.get('uploader',''),'url':'https://www.youtube.com/watch?v='+vid})
    if not videos:raise ValueError('YouTube returned no videos. Try another search or open YouTube in your browser.')
    return videos
