from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms import inlineformset_factory
from django.urls import reverse
from django.contrib.auth.models import User
from django.views import generic
from django.db.models import Q
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.template.loader import get_template
from django.template import Context
from .pdf_utils import PdfPrint
from django.http import HttpResponse
from cgi import escape
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO
from .utils import *
from .models import *
import csv
from django.http import HttpResponse
import datetime
import json as json
import sys

# Create your views here.

def download(request, path):
    file_path = os.path.join(path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    else:
        return redirect('galeniads:index')

@login_required
def index(request):
    # Computing the graphs
    # Get a count of complaints (solved + all)
    all_c = Complaint.objects.count()
    solved_c = Complaint.objects.filter(status='F').count()

    # Get the months that the graph will be for, along with the captions
    months = []
    cdate = datetime.date.today().replace(day=1)
    for _ in range(10):
        cy = cdate.year
        cm = cdate.month
        cqs = Log.objects.filter(date__year=cy, date__month=cm)
        # Get the count of complaints created/resolved in a given month
        months.append({
            'created': cqs.filter(kind='C').count(),
            'resolved': cqs.filter(kind='MD').count(),
            'resets': cqs.filter(kind='ACRMD').count(),
            'caption': cdate.strftime('%b %Y')
        })
        cdate = (cdate - datetime.timedelta(1)).replace(day=1)

    # Reverse, for chronological order
    months.reverse()

    # Collect all the data in a dict, for easy use by js code
    graphdata = {
        'all': all_c,
        'solved': solved_c,
        'monthData': months
    }
    template = 'complaintManager/index.html'
    return render(request, template, {
        'latest_new': Complaint.objects.filter(status='S').order_by('-reported')[:5],
        'latest_progress': Complaint.objects.filter(status='P').order_by('-reported')[:5],
        'graph_json': json.dumps(graphdata)
    })

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    #html  = template.render(context)
    html = render_to_string(
        'complaintManager/keluhan_pdf.html', {
            'complaints': context_dict.get('complaints')
        }
    )
    result = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        resp = HttpResponse(result.getvalue(), content_type='application/octet-stream')
        resp['Content-Disposition'] = 'attachment; filename = "Laporan Keluhan.pdf"'
        return resp
    return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))

def laporan(request):
    #cdate = datetime.date.today().replace(day=1)
    #end_date = cdate # to fetch complaint to this date
    #for _ in range(10):
    #    cdate = (cdate - datetime.timedelta(1)).replace(day=1)
    #start_date = cdate # from this date

    if request.method == 'GET':
        start_date = request.GET['start_date']
        end_date = request.GET['end_date']
        last_complaints = Complaint.objects.filter(reported__range=(start_date, end_date))
        if request.GET['type'] == 'csv':
            # make the csv file
            filename = 'laporan_detail.csv'
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
                #Create field name
                writer.writerow(['Tanggal', 'Deskripsi', 'Status', 'Divisi Yang Mengerjakan',
                    'Prioritas', 'Pemberi Keluhan', 'Asal Instansi Pelapor',
                    'Asal Pelapor (Spesifik)'])

                # Mulai mengisi file
                list = []
                for complaint in last_complaints:
                    list.append(complaint.reported.replace(microsecond=0))
                    list.append(complaint.description)
                    list.append(complaint.status)
                    divisi_list = []
                    for division in complaint.assigned_divisions.all():
                        divisi_list.append(division.code)
                    divisi_string = ", ".join(divisi_list)
                    list.append(divisi_string)
                    list.append(complaint.priority)
                    list.append(complaint.member.user.first_name)
                    list.append(complaint.member.role.origin.name)
                    list.append(complaint.member.role.name)
                    writer.writerow(list)
                    list = []

            download_dir = os.path.join(filename)
            return download(request, download_dir)
        else:
            response = HttpResponse(content_type='application/pdf')
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            filename = 'Laporan Penanganan Keluhan'
            dateduration = 'Jangka Waktu: ' + start_date + ' s.d. ' + end_date
            response['Content-Disposition'] = \
                'attachment; filename={0}.pdf'.format(filename)
            buffer = BytesIO()
            report = PdfPrint(buffer, 'LA4')
            pdf = report.collective_report(last_complaints, filename, dateduration)
            response.write(pdf)
            return response
    else:
        template = 'complaintManager/index.html'
        return render(request, template)

def login(request):
    if request.user.is_authenticated:
        return redirect(reverse('complaintManager:index'))
    template = 'complaintManager/login.html'

    next_url = request.GET.get('next')
    if not next_url:
        next_url = '/'
    if request.method == 'GET':
        return render(request, template, {'next_url': next_url})
    else:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            auth_login(request, user)
            print('A ' + next_url)
            return redirect(next_url)
        else:
            return render(request, template)


@login_required
def logout(request):
    auth_logout(request)
    return redirect(reverse('complaintManager:login'))


@login_required
def complaint_create(request):
    if request.method == 'POST':
        complaint_form = ComplaintCreateForm(request.POST, prefix='complaint')
        location_form = LocationForm(request.POST, prefix='location')
        # print(str(complaint_form.instance.leader))
        if complaint_form.is_valid() and location_form.is_valid() and str(complaint_form.instance.leader)!="None" :
            location_x = location_form.save(commit=False)
            location_x.save()
            complaint = complaint_form.save(commit=False)
            complaint.location = location_x
            complaint.member = request.user.member
            complaint.status = 'S'
            complaint.is_public = False
            complaint.save()
            complaint_form.save_m2m()
            complaint.log_change(request.user, 'C', 'Keluhan berhasil dibuat.')
            # send_email(complaint, True)

            # Create images for current complaint
            for image in request.FILES.getlist('images'):
                compImg = ComplaintImages()
                compImg.src = image
                compImg.complaint = complaint
                compImg.save()

            # informer_form = InformerForm(prefix='informer')
            complaint_form = ComplaintCreateForm(prefix='complaint')
            location_form = LocationForm(prefix='location')
            return redirect(
                "%s?success_create=true" %
                reverse('complaintManager:complaint_list'))
        else:
            complaint_form = ComplaintCreateForm(prefix='complaint')
            location_form = LocationForm(prefix='location')
    else:
        # informer_form = InformerForm(prefix='informer')
        complaint_form = ComplaintCreateForm(prefix='complaint')
        location_form = LocationForm(prefix='location')
    template = 'complaintManager/complaint_create.html'
    return render(request,
                  template,
                  {'complaint_form': complaint_form,
                #    'informer_form': informer_form,
                   'location_form': location_form, })


def complaint_create_public(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, prefix='user')
        informer_form = InformerForm(request.POST, prefix='informer')
        complaint_form = ComplaintCreatePublicForm(
            request.POST, prefix='complaint')
        
        location_form = LocationForm(request.POST, prefix='location')
        if complaint_form.is_valid() and informer_form.is_valid() and location_form.is_valid():
            informer = informer_form.save(commit=False)
            informer.save()
            location_x = location_form.save(commit=False)
            location_x.save()

            complaint = complaint_form.save(commit=False)
            complaint.location = location_x
            complaint.status = 'S'
            complaint.informer = informer
            complaint.is_public = False
            complaint.save()

            # send_email(complaint, True)
            # Create images for current complaint
            for image in request.FILES.getlist('images'):
                compImg = ComplaintImages()
                compImg.src = image
                compImg.complaint = complaint
                compImg.save()

            informer_form = InformerForm(prefix='informer')
            complaint_form = ComplaintCreatePublicForm(prefix='complaint')
            location_form = LocationForm(prefix='location')
            return redirect(reverse('complaintManager:thanks'))

    else:
        informer_form = InformerForm(prefix='informer')
        complaint_form = ComplaintCreatePublicForm(prefix='complaint')
        location_form = LocationForm(prefix='location')
    template = 'complaintManager/complaint_create_public.html'
    return render(request,
                  template,
                  {'complaint_form': complaint_form,
                   'informer_form': informer_form,
                   'location_form': location_form, })

@login_required
def complaint_download(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)

    response = HttpResponse(content_type='application/pdf')
    filename = 'Laporan Penanganan Keluhan \'' + complaint.title + '\''
    response['Content-Disposition'] = \
        'attachment; filename={0}.pdf'.format(filename)
    buffer = BytesIO()
    report = PdfPrint(buffer, 'A4')
    pdf = report.individual_report(request, complaint, filename)
    response.write(pdf)
    return response

def download_to_pdf(template_src, context_dict):
    html  = template.render(context_dict)
    result = BytesIO()

    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        resp = HttpResponse(result.getvalue(), content_type='application/octet-stream')
        resp['Content-Disposition'] = 'attachment; filename = "Laporan Keluhan.pdf"'
        return resp
    return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))

@login_required
def complaint_edit(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    old_complaint = complaint
    complaint_was_finished = complaint.status == 'F'
    if request.method == 'POST':
        complaint_form = ComplaintEditForm(
            request.POST, prefix='complaint', instance=complaint)
        new_complaint = get_object_or_404(Complaint, pk=pk)
        print(complaint_form['title'])
        if complaint_form.is_valid():
            complaint = complaint_form.save(commit=False)
            complaint.save()
            complaint_form.save_m2m()
            change = ""
            old = ""
            new = ""
            if old_complaint.title != new_complaint.title:
                old = old_complaint.title
                new = new_complaint.title
                change = "Judul"
            if old_complaint.assigned_divisions != new_complaint.assigned_divisions:
                old = old_complaint.assigned_divisions
                new = new_complaint.assigned_divisions
                change = "Jenis"
            if old_complaint.leader != new_complaint.leader:
                old = old_complaint.leader
                new = new_complaint.leader
                change = "Divisi"
            if old_complaint.description != new_complaint.description:
                old = old_complaint.description
                new = new_complaint.description
                change = "Deskripsi"
            if old_complaint.priority != new_complaint.priority:
                old = old_complaint.priority
                new = new_complaint.priority
                change = "Prioritas"
            if old_complaint.reported != new_complaint.reported:
                old = old_complaint.reported
                new = new_complaint.reported
                change = "Waktu"
            if old_complaint.status == new_complaint.status and change != "":
                complaint.log_change(request.user, 'AC', change + ' diubah dari "' + str(old) + '" menjadi "' + str(new) + '" oleh '+ request.user.username)

            if complaint_was_finished and complaint.status != 'F':
                complaint.log_change(
                    request.user,
                    'ACRMD',
                    'Status keluhan diubah menjadi belum selesai oleh ' + request.user.username)
            elif not complaint_was_finished and complaint.status == 'F':
                complaint.log_change(
                    request.user, 'MD', 'Status keluhan diubah menjadi sudah selesai oleh ' + request.user.username)
            if complaint.assigned_divisions.count(
            ) > 0 and complaint.log_set.filter(kind='C').count() == 0:
                complaint.log_change(
                    request.user, 'C', 'Keluhan diassign ke divisi oleh  ' + request.user.username)
            return redirect(
                "%s?success_edit=true" %
                reverse('complaintManager:complaint_list'))
    else:
        complaint_form = ComplaintEditForm(
            prefix='complaint', instance=complaint)

    template = 'complaintManager/complaint_edit.html'
    return render(
        request, template, {
            'pk': pk, 'complaint_form': complaint_form})


@login_required
def complaint_delete(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    complaint.delete()
    return redirect('complaintManager:complaint_list')

@login_required
def user_index(request):
    # Query string
    q = ''
    category = ''
    if request.GET.get('q'):
        q = request.GET.get('q')
        users = User.objects.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email__icontains=q)
        )
    elif request.GET.get('category'):
        category = request.GET.get('category')
        users = User.objects.filter(
            Q(member__role__origin__code=category)
        )
    else:
        q = ''
        users = User.objects.filter(Q(member__role__origin__code="Intern"))

    template = 'complaintManager/user_index.html'
    return render(request, template, {'users': users, 'q' : q,'category':category})

@login_required
def user_edit(request, pk):
    origins=Origin.objects.all()
    user = get_object_or_404(User, pk=pk)
    organogram_divisions = user.member.role.divisions.all()
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, prefix='user', instance=user)
        member_form = MemberCreateForm(request.POST,prefix='member',instance=user.member)
        print("member="+str(member_form.is_valid()))
        print("user="+str(user_form.is_valid()))
        if member_form.is_valid() and user_form.is_valid():
            user.save()
            member = member_form.save()
            member.user = user
            member.save()
            messages.success(request, 'Pengguna "' + user.username + '" berhasil disunting')
            return redirect('complaintManager:user_index')
    else:
        user_form = UserEditForm(prefix='user', instance=user)
        member_form = MemberEditForm(prefix='member', instance=user.member)
    template = 'complaintManager/user_edit.html'
    return render(
        request, template, {
            'origins':origins,'pk': pk, 'member_form':member_form, 'user_form': user_form,'organogram_divisions':organogram_divisions})


@login_required
def user_create(request):
    origins = Origin.objects.all()
    if request.method == 'POST':
        user_form = UserForm(request.POST, prefix='user')
        member_form = MemberCreateForm(request.POST, prefix='member')
        print("userform="+str(user_form.is_valid()))
        print("memberform="+str(member_form.is_valid()))
        print(member_form.instance.phone)
        # print(member_form.instance.role.name)
        
        if user_form.is_valid() and member_form.is_valid():
            print("valid")
            user = user_form.save(commit=False)
            user.set_password(request.POST['user-password'])
            user.save()
            member = member_form.save(commit=False)
            member.user = user
            member.save()
            messages.success(request, 'Pengguna "' + user.username + '" berhasil dibuat')
            return redirect('complaintManager:user_index')
        else:
            print("gavalid")
    else:
        
        user_form = UserForm(prefix='user')
        member_form = MemberCreateForm(prefix='member')
    template = 'complaintManager/user_create.html'
    return render(
        request, template, {
            'origins':origins, 'user_form': user_form, 'member_form': member_form })


def getRoles(request):
    #country_name = request.POST['country_name']
    origin_name = request.GET['origin']
    print ("ajax origin_name "+ origin_name)

    result_set = []
    all_origin = []
    # answer = str(origin_name[1:-1])
    selected_origin = Origin.objects.get(name=origin_name)
    print ("selected origin name "+str(selected_origin))
    all_roles = selected_origin.role_set.all()
    for role in all_roles:
        # print "role name", role.name
        result_set.append({'id':role.id,'code':role.code,'name': role.name})
    return HttpResponse(json.dumps(result_set), content_type='application/json')

@login_required
def user_delete(request, pk):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        user.delete()
        messages.success(request, 'Pengguna "' + user.username + '" berhasil dihapus')
    return redirect('complaintManager:user_index')

@login_required
def complaint_status(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    template = 'complaintManager/complaint_manage.html'
    return render(request, template, {'complaint': complaint})

@login_required
def complaint_list(request):
    # Success message
    success_edit = False
    success_create = False
    if request.GET.get('success_edit'):
        success_edit = True
    if request.GET.get('success_create'):
        success_create = True

    # Authorized roles
    if request.user.member.isSuperadmin():
        accessible_complaints = Complaint.objects.all()
    else:
        organogram_divisions = request.user.member.role.divisions.all()
        additional_divisions = request.user.member.additional_division.all()
        accessible_divisions = organogram_divisions | additional_divisions
        accessible_complaints = Complaint.objects.filter(
            assigned_divisions__in=accessible_divisions
        )

    complaints_unpaginated = accessible_complaints.exclude(
        assigned_divisions=None
    )

    # Date filter
    desired_start_date = request.GET.get('start_date')
    desired_end_date = request.GET.get('end_date')
    if desired_start_date:
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(reported__gte=desired_start_date)
        )
    if desired_end_date:
        desired_end_date = desired_end_date + ' 23:59:59'
        print("Date is " + str(desired_end_date))
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(reported__lte=desired_end_date)
        )

    orderings = {
        'none': '-reported',  # The default is to order by report time
        'reported': '-reported',  # Default may change one day
        'title': 'title',
    }

    filters = {
        'done': Q(status='F'),
        'progress': Q(status='P'),
        'new': Q(status='S'),
    }

    search_query = request.GET.get('search')
    if search_query :
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(title__icontains=search_query)
            | Q(informer__name__icontains=search_query)
        )

    desired_order = request.GET.get('sort', 'none')
    desired_filter = request.GET.getlist('filter', ['done', 'progress', 'new'])

    filter_qs = [filters[f] for f in desired_filter]
    filter_q = filter_qs[0]
    for q in filter_qs[1:]:
        filter_q = filter_q | q

    complaints_unpaginated = (
        complaints_unpaginated.order_by(orderings[desired_order])
                              .filter(filter_q)
    )

    paginator = Paginator(complaints_unpaginated, 10)

    page = request.GET.get('page')
    try:
        complaints = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        complaints = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        complaints = paginator.page(paginator.num_pages)

    template = 'complaintManager/list-keluhan.html'
    return render(
        request, template, {
            'complaints': complaints,
            'title': 'Daftar Keluhan Masuk',
            'success_edit': success_edit,
            'success_create': success_create,
            'search_query' : search_query,
            'list_state': {
                'filter': desired_filter,
                'sort': desired_order
            },
            'end_date': desired_end_date,
            'start_date': desired_start_date
        })

@login_required
def complaint_list_out(request):
    # Success message
    success_edit = False
    success_create = False
    if request.GET.get('success_edit'):
        success_edit = True
    if request.GET.get('success_create'):
        success_create = True

    # Authorized roles
    accessible_divisions = request.user.member.role.divisions.all()
    accessible_complaints = Complaint.objects.filter(
        member__user__email__iexact=request.user.email
    )

    complaints_unpaginated = accessible_complaints.exclude(
        assigned_divisions=None
    )

    # Date filter
    desired_start_date = request.GET.get('start_date')
    desired_end_date = request.GET.get('end_date')
    if desired_start_date:
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(reported__gte=desired_start_date)
        )
    if desired_end_date:
        desired_end_date = desired_end_date + ' 23:59:59'
        print("Date is " + str(desired_end_date))
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(reported__lte=desired_end_date)
        )

    orderings = {
        'none': '-reported',  # The default is to order by report time
        'reported': '-reported',  # Default may change one day
        'title': 'title',
    }

    filters = {
        'done': Q(status='F'),
        'progress': Q(status='P'),
        'new': Q(status='S'),
    }

    search_query = request.GET.get('search')
    if search_query :
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(title__icontains=search_query)
            | Q(informer__name__icontains=search_query)
        )

    desired_order = request.GET.get('sort', 'none')
    desired_filter = request.GET.getlist('filter', ['done', 'progress', 'new'])

    filter_qs = [filters[f] for f in desired_filter]
    filter_q = filter_qs[0]
    for q in filter_qs[1:]:
        filter_q = filter_q | q

    complaints_unpaginated = (
        complaints_unpaginated.order_by(orderings[desired_order])
                              .filter(filter_q)
    )

    paginator = Paginator(complaints_unpaginated, 10)

    page = request.GET.get('page')
    try:
        complaints = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        complaints = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        complaints = paginator.page(paginator.num_pages)

    template = 'complaintManager/list-keluhan.html'
    return render(
        request, template, {
            'complaints': complaints,
            'title': 'Daftar Keluhan Keluar',
            'success_edit': success_edit,
            'success_create': success_create,
            'search_query' : search_query,
            'list_state': {
                'filter': desired_filter,
                'sort': desired_order
            },
            'end_date': desired_end_date,
            'start_date': desired_start_date
        })


@login_required
def complaint_list_public(request):
    complaints_unpaginated = Complaint.objects.filter(
        assigned_divisions=None).order_by('-reported')

    search_query = request.GET.get('search')
    if search_query :
        complaints_unpaginated = complaints_unpaginated.filter(
            Q(title__icontains=search_query)
            | Q(informer__name__icontains=search_query)
        )

    paginator = Paginator(complaints_unpaginated, 10)

    page = request.GET.get('page')
    try:
        complaints = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        complaints = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        complaints = paginator.page(paginator.num_pages)

    template = 'complaintManager/complaint_public_index.html'
    return render(
        request, template, {
            'complaints': complaints,
            'title': 'Daftar Keluhan Publik',
            'search_query': search_query})


@login_required
def role_management_index(request):
    q = ''
    category = ''
    if request.GET.get('q'):
        q = request.GET.get('q')
        roles = Role.objects.filter(
            Q(name__icontains=q)
        )
    else:
        roles = Role.objects.filter(Q(origin__code="Intern"))
    divisions = Division.objects.all()
    form = ExternalUserOriginForm()
    division_form = DivisionForm()
    form_edit = ExternalUserOriginForm(prefix='edit')
    template = 'complaintManager/role_management_index.html'
    return render(
        request, template, {
            'division_form':division_form,'divisions':divisions,'roles':roles, 'form': form, 'form_edit': form_edit, 'q': q, 'category': category
        })

@login_required
def role_management_add(request):
    if request.method == 'POST':
        role_form = RoleForm(request.POST)
        if role_form.is_valid():
            print("valid")
            role = role_form.save(commit=False)
            role.origin = Origin(id=3)
            role.save()
            role_form.save_m2m()
            return redirect('complaintManager:role_management_index')
        else:
            print("ga valid :(")
    else:
        role_form = RoleForm()
    template = 'complaintManager/role_management_add.html'
    return render(
        request, template, {
            'role_form':role_form })

@login_required
def division_add(request):
    form = DivisionForm(request.POST)
    if form.is_valid():
        form.save() 
    return redirect("%s?success_create=true" % reverse('complaintManager:role_management_index'))

@login_required
def role_management_edit(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        print("masuk valid")
        role_form = RoleForm(request.POST, instance=role)
        print(role_form.instance.name)
        for division in role_form.instance.divisions.all():
            print(division.name)
        if role_form.is_valid():
            role_form.save()
            return redirect('complaintManager:role_management_index')
    else:
        print("valid")
        role_form = RoleForm(instance=role)
    template = 'complaintManager/role_management_edit.html'
    return render(
        request, template, {
            'pk': pk, 'role_form':role_form})

@login_required
def division_edit(request, pk):
    division = get_object_or_404(Division, pk=pk)
    form = DivisionForm(request.POST, instance=division)
    if form.is_valid():
        print("Masuk valid")
        print(form.instance.name)
        print(form.instance.code)
        form.save()
    else:
        print("invalid form")
    return redirect(reverse('complaintManager:role_management_index'))

@login_required
def role_management_delete(request, pk):
    if request.method == "POST":
        role = Role.objects.get(pk=pk)
        role.delete()
    return redirect(reverse('complaintManager:role_management_index'))

@login_required
def division_delete(request, pk):
    if request.method == "POST":
        division = Division.objects.get(pk=pk)
        division.delete()
    return redirect(reverse('complaintManager:role_management_index'))

@login_required
def external_user_origin_index(request):
    q = ''
    category = ''
    if request.GET.get('q'):
        q = request.GET.get('q')
        roles = Role.objects.filter(
            Q(name__icontains=q)
        )
    elif request.GET.get('category'):
        category = request.GET.get('category')
        roles = Role.objects.filter(
            Q(origin__code=category)
        )
    else:
        roles = Role.objects.filter(~Q(origin__code="Intern"))
    form = ExternalUserOriginForm()
    form_edit = ExternalUserOriginForm(prefix='edit')
    template = 'complaintManager/external_user_origin_index.html'
    return render(
        request, template, {
            'roles':roles, 'form': form, 'form_edit': form_edit, 'q': q, 'category': category
        })


@login_required
def informer_origin_add(request):
    form = InformerOriginForm(request.POST)
    if form.is_valid():
        form.save()  
    return redirect(reverse('complaintManager:informer_origin_index'))

@login_required
def external_user_origin_add(request):
    form = ExternalUserOriginForm(request.POST)
    if form.is_valid():
        form.save() 
    return redirect("%s?success_create=true" % reverse('complaintManager:external_user_origin_index'))

@login_required
def informer_origin_edit(request, pk):
    informer_origin = get_object_or_404(InformerOrigin, pk=pk)
    form = InformerOriginForm(request.POST, instance=informer_origin)
    if form.is_valid():
        form.save()
    return redirect(reverse('complaintManager:informer_origin_index'))

@login_required
def external_user_origin_edit(request, pk):
    external_user_origin = get_object_or_404(Role, pk=pk)
    form = ExternalUserOriginForm(request.POST, instance=external_user_origin)
    if form.is_valid():
        print("Masuk valid")
        form.save()
    else:
        print("invalid form")
    return redirect(reverse('complaintManager:external_user_origin_index'))


@login_required
def informer_origin_delete(request, pk):
    if request.method == "POST":
        origin = InformerOrigin.objects.get(pk=pk)
        origin.delete()
    return redirect(reverse('complaintManager:informer_origin_index'))

@login_required
def external_user_origin_delete(request, pk):
    if request.method == "POST":
        role = Role.objects.get(pk=pk)
        role.delete()
    return redirect(reverse('complaintManager:external_user_origin_index'))


@login_required
def complaint_list_uk(request):
    # complaints = Complaint.objects.exclude(assigned_divisions=None)
    # dvs = request.user.member.role.divisions.all();
    un = request.user.username  # cara dapetin username
    # print("username" + un)
    us = Member.objects.get(user=request.user)
    print(us.role)
    # Divisi sama Role hubungannya apa?
    div = get_object_or_404(Division, name=us.role.name)  # ini masih salah
    complaints = Complaint.objects.filter(assigned_divisions=div)
    print(complaints)
    template = 'complaintManager/list-keluhan.html'
    return render(
        request, template, {
            'complaints': complaints, 'title': 'Daftar Keluhan'})


@login_required
def update_status(request, pk):
    print('update')
    complaint = Complaint.objects.get(pk=pk)
    logs = Log.objects.filter(complaint=complaint, creator=request.user)
    if complaint.status == 'S':
        print(complaint.status)
        complaint.status = 'P'
        complaint.log_change(request.user, 'MP', 'Keluhan sedang dikerjakan.')
    elif complaint.status == 'P':
        print(complaint.status)
        complaint.status = 'F'
        complaint.log_change(request.user, 'MD', 'Keluhan selesai dikerjakan.')
    complaint.save()
    # send_email(complaint, False)
    return redirect(reverse('complaintManager:complaint_status', args={pk}))


@login_required
def add_worker(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    div = get_object_or_404(Division, name=request.user.member.role.name)
    if request.method == 'POST':
        name = request.POST['name']
        worker = Worker(name=name, complaint=complaint, division=div)
        worker.save()
        complaint.log_change(
            request.user,
            'AW',
            '{} menjadi pekerja pada keluhan ini.'.format(worker.name))
    return redirect(reverse('complaintManager:complaint_status', args={pk}))


@login_required
def add_log(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST':
        des = request.POST['description']
    complaint.log_change(
        request.user,
        'AL',
        des
    )
    return redirect(reverse('complaintManager:complaint_status', args={pk}))

@login_required
def edit_log(request, pk):
    if request.method == 'POST':
        logPK = request.POST['logPK']
        log = get_object_or_404(Log, pk=logPK)
        des = request.POST['description']
        log.description = des
        log.save()
    return redirect(reverse('complaintManager:complaint_status', args={pk}))

@login_required
def delete_log(request, pk):
    if request.method == 'POST':
        logPK = request.POST['logPK']
        log = get_object_or_404(Log, pk=logPK)
        log.delete()
    return redirect(reverse('complaintManager:complaint_status', args={pk}))

@login_required
def add_image_log(request, pk):
    if request.method == 'POST':
        logPK = request.POST['logPK']
        log = get_object_or_404(Log, pk=logPK)
        complaint = log.complaint

        for image in request.FILES.getlist('images'):
            compImg = ComplaintImages()
            compImg.src = image
            compImg.complaint = complaint
            compImg.log = log
            compImg.save()

    return redirect(reverse('complaintManager:complaint_status', args={pk}))

def thanks(request):
    return render(request, 'complaintManager/thanks.html')
