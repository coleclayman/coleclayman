import urllib
import hashlib
import requests, datetime, pytz
import json
import subprocess

from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse, JsonResponse, Http404
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import *
from .forms import *

# Create your views here.

def handler404(request):
    response = render_to_response('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def handler500(request):
    response = render_to_response('500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response


def project_detail(request, slug):
    context = {}
    proj = Project.objects.filter(slug=slug)
    
    if not proj.exists():
        raise Http404("sorry, you're lost.")

    context['project'] = proj.first()

    return render_to_response('project_detail.html', context, context_instance=RequestContext(request))


def projects(request):
    context = {}
    context['projects'] = Project.objects.all()

    return render_to_response('projects.html', context, context_instance=RequestContext(request))


def choose_schedule(request):
    context = {}

    now = datetime.datetime(2016, 1, 1, 8, 0, 0)
    django_now = timezone.localtime(timezone.now())

    china = pytz.timezone('Asia/Shanghai')
    china_now = china.localize(now)

    user_tz = django_now.tzinfo
    user_tz_now = user_tz.localize(now)

    hours = (china_now - user_tz_now).seconds / 60 / 60 + 9
    context['start_hour'] = hours
    print "%s:00 is the time they should start" % hours

    return render_to_response('choose_schedule.html', context, context_instance=RequestContext(request))


def new_home(request):
    context = {}
    # print michelle
    if request.GET.get('wc'):
        context['hide'] = True

    context['fade_in_time'] = 300

    return render_to_response('new_home.html', context, context_instance=RequestContext(request))


def bio(request):
    context = {}
    return render_to_response('bio.html', context, context_instance=RequestContext(request))


def vc(request):
    context = {}
    return render_to_response('vc.html', context, context_instance=RequestContext(request))


def home(request):
    context = {}
    context['home'] = True

    if request.method == 'POST':
        form = ContactForm(request.POST)
        context['form'] = form
        print "hello"
        if form.is_valid():
            print 'yikes'
            send_mail("coleclayman portfolios: %s" % form.cleaned_data['name'], form.cleaned_data['message'] + "\n" + form.cleaned_data['phone'], form.cleaned_data['email'], [settings.EMAIL_HOST_USER], fail_silently=False)
            return render(request, 'thanks.html')
    else:
        form = ContactForm()
        context['form'] = form


    return render_to_response('home.html', context, context_instance=RequestContext(request))


def video_call(request, pk, slug=None):
    context = {}

    video_call = VideoCall.objects.get(pk=pk)

    context['video_call'] = video_call
    context['create'] = True if slug == "parent" else False

    return render(request, 'video_call.html', context)


@csrf_exempt
def video_call_ajax(request):
    if request.POST:
        username = request.POST.get('atypical', False)
        password = request.POST.get('more_atypical', False)

        if not username and password:
            return HttpResponse("bad call")

        # auth_user = authenticate(username=username, password=password)

        # if auth_user is None:
        if username != 'atypical' and password != 'more_atypical':
            return HttpResponse("bad credentials")

        val = request.POST.get('val', '').strip()
        number = request.POST.get('number', '').strip()
        pk = request.POST.get('pk', '').strip()

        try:
            video_call = VideoCall.objects.get(pk=pk)
        except Exception as e:
            return HttpResponse('bad pk')

        if not val or not number:
            return HttpResponse('incomplete call')

        if number == '1':
            video_call.p1_key = val
            video_call.p1_active = True
            video_call.p2_key = ""
            video_call.save()

        if number == '2':
            video_call.p2_key = val
            video_call.p2_active = True
            video_call.save()

        return HttpResponse('success')

    if request.GET:
        username = request.GET.get('atypical', False)
        password = request.GET.get('more_atypical', False)

        if not username and password:
            return HttpResponse("bad call")

        # auth_user = authenticate(username=username, password=password)

        # if auth_user is None:
        
        if username != 'atypical' and password != 'more_atypical':
            return HttpResponse("bad credentials")

        number = request.GET.get('number', '').strip()
        pk = request.GET.get('pk', '').strip()

        try:
            video_call = VideoCall.objects.get(pk=pk)
        except Exception as e:
            return HttpResponse('bad pk')

        if not number:
            return HttpResponse('incomplete call')

        if number == '1':
            return HttpResponse('%s' % video_call.p1_key)

        if number == '2':
            return HttpResponse('%s' % video_call.p2_key)

        return HttpResponse('bad number call')

    return HttpResponse("bad method")

def ugf(request):
    context = {}
    form = CRAForm(request.POST or None)

    context['form'] = form
    if request.method == "POST":
        if form.is_valid():
            context['separate'] = request.POST.get('together', False) == 'separate'
            naics_code = form.cleaned_data.get('naics', False)
            if naics_code:
                naics_results = check_naics_code(naics_code)
                if naics_results['success']:
                    context['max_employees'] = naics_results['num_employees']
                else:
                    print "fail on naics..."


            street_address = form.cleaned_data['street_address']
            if form.cleaned_data.get('city', False):
                street_address += " " + form.cleaned_data['city']
            if form.cleaned_data.get('state', False):
                street_address += " " + form.cleaned_data['state']
            
            results = check_cra_address(street_address)
            context['success'] = results['success']
            if results['success']:
                # successful address!
                context['cra_qualified'] = results['cra_qualified']
                context['address'] = results['address']
                context['min_income'] = results['min_income']
                context['income_level'] = results['income_level'].lower()
                if results['cra_qualified']:
                    # CRA qualified
                    context['results'] = "This address is CRA qualified!"
                else:
                    context['results'] = "This address is NOT CRA qualified."

            else:
                context['results'] = "Uh oh, there was an error with that address."
                print results['message']
        else:
            print "invalid"


    return render_to_response('ugf.html', context, context_instance=RequestContext(request))



def check_cra_address(address):
    return_dict = {}

    payload = {
        'Host': 'geomap.ffiec.gov',
        'Connection': 'keep-alive',
        'Content-Length': 82,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Origin': 'https://geomap.ffiec.gov',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
        'Content-Type': 'application/json; charset=UTF-8',
        'Referer': 'https://geomap.ffiec.gov/FFIECGeocMap/GeocodeMap1.aspx',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.8',
        'Cookie': 'BIGipServergeomap.ffiec.gov.app~geomap.ffiec.gov_pool=2638334084.20480.0000; _ga=GA1.2.130982089.1469575894; _gat=1',
    }

    
    geocode_url = 'https://geomap.ffiec.gov/FFIECGeocMap/GeocodeMap1.aspx/GetGeocodeData'
    geocode_data = '{sSingleLine: "%s", iCensusYear: "2016"}' % (address)

    geo_resp = requests.post(geocode_url, data=geocode_data, headers=payload)


    try:
        geo_json = geo_resp.json().get('d', False)
    except Exception, e:
        return_dict['success'] = False
        return_dict['message'] = "bad request; no json() - " + geo_resp.text

        return return_dict

    if not geo_json:
        return_dict['success'] = False
        return_dict['message'] = "bad request; has json but no d"
        
        return return_dict


    if geo_json.get('iCensusYear') < 10:
        return_dict['success'] = False
        return_dict['message'] = 'fail, here is the message: ' + geo_json.get('sMsg')
        
        return return_dict

    address_string = "%s<br>%s<br>%s<br>%s" % ( geo_json.get('sAddress'), 
                                                      geo_json.get('sCityName'),
                                                      geo_json.get('sCountyName'),
                                                      geo_json.get('sStateName') )


    url = 'https://geomap.ffiec.gov/FFIECGeocMap/GeocodeMap1.aspx/GetCensusDataNoMSA'

    state_code = geo_json.get('sStateCode')
    county_code = geo_json.get('sCountyCode')
    tract_code = geo_json.get('sTractCode')

    data = '{sStateCode: "%s", sCountyCode: "%s", sTractCode: "%s", iCensusYear: "2016"}' % (state_code, county_code, tract_code)
    response = requests.post(url, data=data, headers=payload)

    json = response.json()
    # print json.get('d')
    income_json = json.get('d', {'sIncome_Indicator': 'Failed request.'})
    income_level = income_json.get('sIncome_Indicator', 'Failed request.')

    if "Failed request." in income_level:
        return_dict['success'] = False
        return_dict['message'] = "Bad json of second url"
        
        return return_dict

    est_income = float( income_json.get('sEst_Income') )
    tract_income = float( income_json.get('sHUD_est_MSA_MFI') )

    lowest_income = min(est_income, tract_income)
    min_income = lowest_income * 0.8


    print 'Income Level for above address is:', income_level
    print "CRA Qualified:", "Yes!" if income_level == "Low" or income_level == "Moderate" else "No..."

    cra_qualified = income_level == "Low" or income_level == "Moderate"
    
    return_dict['cra_qualified'] = cra_qualified
    return_dict['address'] = address_string
    return_dict['min_income'] = int(min_income)
    return_dict['income_level'] = income_level
    return_dict['success'] = True

    return return_dict


def check_naics_code(naics_code):
    print naics_code
    response = requests.get('https://www.federalregister.gov/articles/2016/01/26/2016-00924/small-business-size-standards-for-manufacturing')

    text = response.text

    match = '<td class="">%s</td>' % naics_code

    if match in text:
        text = text.partition(match)[2].partition('</td>')[2]
        num_employees = text.partition('<td>')[2].partition('</td>')[0]
        # print "match in text"
        # print "num_employees", num_employees
        return {'success': True, 'num_employees': num_employees }
    else:
        # print "no match in text"
        return {'success': False, }


def ajax_definition(request):

    query = request.GET.get('q', False)

    if not query:
        return HttpResponse('no 2')

    query = query.lower()

    # if query isn't defined already in our database, then 
    # defs, created = WordDefinition.objects.get_or_create(english_word=query)
    # if not created:
    #     return defs.chinese_defs_dict
    # if created, query the db and save results

    # verify query is urllib-ed

    res = requests.get('https://api.pearson.com/v2/dictionaries/ldec/entries?headword=%s&apikey=BfU9UKkd6c2owEjppG9wAdHgwfdkClXO' % query) 

    results = res.json().get('results', False)

    if not results:
        return HttpResponse('no 2')

    word_dict = {}
    word_dict['words'] = []

    for word in results[:3]:
        new_word = {}
        new_word['word'] = word.get('headword')
        new_word['pos'] = word.get('part_of_speech')
        senses = word.get('senses', [])
        
        if senses:        
            new_word['def'] = senses[0].get('translation')
        else:
            continue

        word_dict['words'].append(new_word)

    return JsonResponse(word_dict, safe=False)


BOOKS = {
    'bom': 'Book of Mormon',
    'dc': 'Doctrine and Covenants',
    'bible': 'Bible',
    'pgp': 'Pearl of Great Price',
}

def open_scriptures(request):
    context = {}

    if request.POST:
        form = ScriptureOpener(request.POST)

        if form.is_valid():
            search_term = form.cleaned_data.get('open_scriptures')
            while '  ' in search_term:
                search_term = search_term.replace('  ', ' ', 1)
            
            terms = search_term.lower().split(';')
            links = []

            for term in terms:
                if not term.strip():
                    continue
                    
                term = term.replace('doctrine & covenants', 'D&C')
                term = term.replace('doctrine and covenants', 'D&C')
                the_term = urllib.quote_plus(term.strip())

                search_url = "https://www.lds.org/scriptures/search?lang=eng&query=%s" % the_term

                r = requests.get(search_url)
                links.append(r.url)

            context['links'] = links
            context['search_term'] = search_term

    return render(request, 'open_scriptures.html', context)

def check_page_number(request):
    context = {}

    if request.POST:
        form = ScripturePageSearch(request.POST)
        if form.is_valid():
            book_of_scripture = form.cleaned_data.get('book_of_scripture')
            page_number = form.cleaned_data.get('page_number')
            try:
                val = ScriptureCache.objects.get(book_of_scripture=book_of_scripture, pagenumber__page_number=page_number)
            except ScriptureCache.DoesNotExist as e:
                val = False
                context['failure'] = True

            context['location'] = val
            context['book'] = book_of_scripture or False
            context['book_long'] = BOOKS.get(book_of_scripture, False)
            if book_of_scripture == "bible" and val:
                page_number = int(page_number)
                context['testament'] = "new" if page_number >= 1187 else "old"
            context['page'] = page_number or False

    return render(request, 'check_page_number.html', context)


@csrf_exempt
def check_page_number_json(request):
    if request.POST:
        form = ScripturePageSearch(request.POST)
        if form.is_valid():
            book_of_scripture = form.cleaned_data.get('book_of_scripture')
            page_number = form.cleaned_data.get('page_number')

            try:
                val = ScriptureCache.objects.get(book_of_scripture=book_of_scripture, pagenumber__page_number=page_number)
            except ScriptureCache.DoesNotExist as e:
                val = False

            if val:
                return JsonResponse(
                    {'result': 'success', 'location': str(val)}, 
                    safe=False )
            return JsonResponse(
                {'result': 'failure'}, 
                safe=False )

    return HttpResponse('bad call.')


@csrf_exempt
def create_new_budget_item(request):
    # import pdb; pdb.set_trace()
    if not request.POST:
        try:
            request_post = json.loads(request.body)
        except Exception, e:
            print e
            return JsonResponse({'result': 'failure'}, safe=False )

        if not request_post:
            print "no post"
            return JsonResponse({'result': 'failure'}, safe=False )

    form = BudgetItemCreateForm(request.POST or request_post)
    if form.is_valid():
        secret_code = form.cleaned_data.get('secret_code')
        month = form.cleaned_data.get('month')

        # verifying correct user
        if secret_code != hashlib.sha256(month).hexdigest():
            print "bad secret code"
            return JsonResponse({'result': 'failure'}, safe=False )

        title = form.cleaned_data.get('title')
        category = form.cleaned_data.get('category')
        value = form.cleaned_data.get('value')

        new_item = BudgetItem.objects.create(title=title, category=category, value=value)
        return JsonResponse({'result': 'success'}, safe=True)

    else:
        print "bad post"
        return JsonResponse(
                {'result': 'failure'}, 
                safe=False )


@csrf_exempt
def get_all_undownloaded_items(request):
    if not request.POST:
        print "no post"
        return JsonResponse({'result': 'failure'}, safe=False )

    form = BudgetItemVerifyForm(request.POST)

    if form.is_valid():
        secret_code = form.cleaned_data.get('secret_code')
        month = form.cleaned_data.get('month')

        # verifying correct user
        if secret_code != hashlib.sha256(month).hexdigest():
            print "bad secret code"
            return JsonResponse({'result': 'failure'}, safe=False )

        items = BudgetItem.objects.filter(downloaded=False)
        
        item_list = []
        for item in items:
            item_list.append( item.jsonify() )

        return_json = {
            'result': "success",
            'items': item_list
        }
        items.update(downloaded=True)

        return JsonResponse(return_json, safe=False )

    else:
        print "bad post"
        return JsonResponse(
                {'result': 'failure'}, 
                safe=False )


@csrf_exempt
def spotify_access_token(request):
    if not request.method == "POST":
        return JsonResponse({'result': 'failure'}, safe=False)

    headers = {
        'Authorization': 'Basic YTRhODM3NzNiNDRmNGVkZjgxOThhZjM2OGZkYzc4MTA6NGJlOTYyY2Y3ZjVkNDhjNjlmY2VkMGZkYTU5ODVjOGI=',
    }    

    data = {
      'grant_type': 'client_credentials'
    }

    response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)

    json_response = JsonResponse(response.json(), safe=False)
    json_response['Access-Control-Allow-Origin'] = '*'
    return json_response


@csrf_exempt
def trigger_ronald_rump(request):
    if not request.method == "POST":
        return JsonResponse({'result': 'failure'}, safe=False) 
    
    form = ScriptureOpener({"open_scriptures": request.body})
    if not form.is_valid():
        return JsonResponse({'result': 'failure'}, safe=False) 

    if form.cleaned_data.get("open_scriptures") == "this is definitely the secret code no one will hack this":
        subprocess.Popen(["/sites/virtualenvs/coleclayman/bin/python", "/scripts/trumpify.py"])
        return JsonResponse({'result': 'success'}, safe=False)
    
    return JsonResponse({'result': 'failure'}, safe=False) 


def jacob(request):
    if request.method != "GET":
        return Http404()

    res = request.GET.get("sc", False)

    if not res:
        res

    form = ScriptureOpener({"open_scriptures": res})
    if not form.is_valid():
        return JsonResponse({'result': 'failure'}, safe=False) 
    

    if form.cleaned_data.get("open_scriptures") == "this-is-definitely-the-secret-code-no-one-will-hack-this":
        headers = {
            "Authorization": "Basic Njg2ZjVhNWIxYmRiNGQ5ODBmM2Q3MTI0Nzc5N2Q5YWY6YXBpX3Rva2Vu"
        }
        url = "https://toggl.com/reports/api/v2/weekly?user_agent=jacobclarke718@gmail.com&workspace_id=1682814"
        resp = requests.get(url, headers=headers)
        return JsonResponse(resp.json(), safe=False)

    return JsonResponse({'result': 'failure'}, safe=False) 
    
