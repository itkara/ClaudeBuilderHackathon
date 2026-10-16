import json
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from django.test import SimpleTestCase, RequestFactory
from . import matcher, views, demo


class EligibilityTests(SimpleTestCase):
    def setUp(self):
        reservation = patch('matching.views.reserve_live_search', return_value=True)
        reservation.start()
        self.addCleanup(reservation.stop)
        self.now = datetime(2026, 10, 16, tzinfo=timezone.utc)
        self.profile = {'gradYear': 2027, 'classification': '2:1', 'subjectTags': ['computer-science'],
                        'rightToWork': 'UK', 'skills': ['python', 'git'], 'experiences': []}
        self.role = {'id': 'test', 'stages': ['final'], 'minClassification': '2:1',
                     'subjects': ['computer-science'], 'rightToWork': 'UK',
                     'skillsRequired': ['python', 'git'], 'skillsPreferred': ['sql']}

    def test_all_requirements_with_missing_optional_skill_is_eligible(self):
        result = matcher.evaluate(self.profile, self.role, self.now)
        self.assertEqual(result['tier'], 'eligible')
        self.assertEqual(result['missingPreferred'], ['sql'])

    def test_missing_required_skill_is_excluded(self):
        result = matcher.evaluate(self.profile, {**self.role, 'skillsRequired': ['python', 'sql']}, self.now)
        self.assertEqual(matcher.rank([result]), [])

    def test_hard_requirements_are_all_enforced(self):
        for change in [{'gradYear': 2028}, {'classification': '2:2'}, {'subjectTags': ['humanities']}, {'rightToWork': ''}]:
            with self.subTest(change=change):
                self.assertEqual(matcher.evaluate({**self.profile, **change}, self.role, self.now)['tier'], 'hidden')
        self.assertEqual(matcher.evaluate(self.profile, {**self.role, 'closes': '2026-10-15'}, self.now)['tier'], 'hidden')

    def test_skill_substrings_do_not_count(self):
        self.assertFalse(matcher.has_skill({'skills': []}, 'git', 'digital marketing'))
        self.assertFalse(matcher.has_skill({'skills': []}, 'java', 'javascript'))
        self.assertTrue(matcher.has_skill({'skills': []}, 'c++', 'built a c++ project'))

    @patch.dict('os.environ', {'ADZUNA_APP_ID': 'test', 'ADZUNA_APP_KEY': 'test'})
    @patch('matching.views.claude.has_key', return_value=True)
    @patch('matching.views.claude.assess_live_jobs')
    @patch('matching.views.requests.get')
    def test_live_search_filters_unverified_and_missing_skills(self, fetch, assess, has_key):
        fetch.return_value = Mock(json=lambda: {'results': [
            {'id': str(i), 'title': 'Graduate developer', 'description': 'Python required', 'redirect_url': 'https://example.com/job'}
            for i in range(4)]})
        assess.return_value = [
            {'id': 'adzuna-0', 'eligible': True, 'reasons': ['Python evidenced'], 'role': self.role},
            {'id': 'adzuna-1', 'eligible': True, 'reasons': ['Python evidenced'], 'role': {**self.role, 'skillsRequired': ['sql']}},
            {'id': 'adzuna-2', 'eligible': False, 'reasons': ['Experience unknown'], 'role': self.role},
        ]
        request = RequestFactory().post('/api/live-jobs', data=json.dumps({'profile': self.profile}), content_type='application/json')
        request.user = Mock()
        response = views.live_jobs(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual([r['role']['id'] for r in data['jobs']], ['adzuna-0'])
        self.assertEqual(data['hiddenCount'], 3)
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_live_search_requires_profile(self):
        request = RequestFactory().post('/api/live-jobs', data='{}', content_type='application/json')
        self.assertEqual(views.live_jobs(request).status_code, 400)

    @patch.dict('os.environ', {'ADZUNA_APP_ID': 'test', 'ADZUNA_APP_KEY': 'test'})
    @patch('matching.views.claude.has_key', return_value=False)
    @patch('matching.views.claude.assess_live_jobs')
    @patch('matching.views.requests.get')
    def test_live_search_without_ai_uses_local_rules(self, fetch, ai_assess, has_key):
        fetch.return_value = Mock(json=lambda: {'results': [
            {'id': 'good', 'title': 'Graduate developer', 'description': 'Python and Git skills required.', 'redirect_url': 'https://example.com/good'},
            {'id': 'missing', 'title': 'Graduate analyst', 'description': 'SQL skills required.', 'redirect_url': 'https://example.com/missing'},
            {'id': 'senior', 'title': 'Senior developer', 'description': 'Python skills required.', 'redirect_url': 'https://example.com/senior'},
            {'id': 'preview', 'title': 'Graduate analyst', 'description': 'About our organisation…', 'redirect_url': 'https://example.com/preview'}]})
        request = RequestFactory().post('/api/live-jobs', data=json.dumps({'profile': self.profile}), content_type='application/json')
        request.user = Mock()
        response = views.live_jobs(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([j['role']['id'] for j in json.loads(response.content)['jobs']], ['adzuna-good'])
        data = json.loads(response.content)
        self.assertEqual([j['role']['id'] for j in data['reviewJobs']], ['adzuna-preview'])
        self.assertTrue(all(j['role']['eligibilityUnverified'] for j in data['reviewJobs']))
        self.assertEqual((data['fetchedCount'],data['unmetCount'],data['unclearCount'],data['skippedCount']), (4,2,1,0))
        self.assertEqual(fetch.call_args.kwargs['params']['results_per_page'], 50)
        self.assertEqual(fetch.call_args.kwargs['params']['app_id'], 'test')
        ai_assess.assert_not_called()

    def test_cv_extraction_does_not_invent_skills_or_first_class_grade(self):
        profile = demo.demo_profile('Alex Example\nDigital marketing assistant tutoring first-year students. Graduating 2027.')
        self.assertNotIn('git', profile['skills'])
        self.assertIsNone(profile['classification'])

    @patch('matching.views.claude.has_key', return_value=False)
    def test_empty_demo_matches_explain_exclusions(self, has_key):
        profile = {**self.profile, 'skills': [], 'rightToWork': ''}
        request = RequestFactory().post('/api/match', data=json.dumps({'profile': profile}), content_type='application/json')
        response = views.match(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['results'], [])
        self.assertEqual(len(data['excluded']), data['hiddenCount'])
        self.assertTrue(all(role['reasons'] for role in data['excluded']))

    def test_example_cv_qualifies_for_seven_sample_roles(self):
        from pathlib import Path
        from django.conf import settings
        script = (Path(settings.BASE_DIR) / 'static/app.js').read_text()
        cv = script.split('const EXAMPLE_CV = `', 1)[1].split('`;', 1)[0]
        profile = demo.demo_profile(cv)
        profile.update(subjectTags=['physics'], rightToWork='UK')
        results = matcher.rank(matcher.match_all(profile, views.load_roles(), self.now))
        self.assertGreaterEqual(len(results), 7)
        self.assertEqual({r['role']['id'] for r in results}, {'s02','s03','s04','s06','s09','s11','s12'})
        self.assertTrue(all(result['fit']==100 for result in results))
        roles=views.load_roles()
        maximum=max(sum(stage in role['stages'] for role in roles) for stage in ('early','penultimate','final'))
        self.assertEqual(len(results),maximum)


from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import DailyAIUsage


class GenerationAllowanceTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='quota-test'))

    @patch.dict('os.environ', {'HIREATIONSHIP_DAILY_GENERATION_LIMIT': '4', 'ANTHROPIC_API_KEY': ''})
    def test_saving_is_free_and_only_four_generations_are_allowed(self):
        self.assertEqual(self.client.get('/api/generation-quota').json()['remaining'], 4)
        self.assertEqual(self.client.post('/api/workspace', data=json.dumps({'apps': [{'id': 'saved-role'}]}), content_type='application/json').status_code, 200)
        self.assertEqual(self.client.get('/api/generation-quota').json()['remaining'], 4)
        profile = {'gradYear': 2027, 'skills': ['python'], 'experiences': []}
        role = {'title': 'Example', 'skillsRequired': ['python']}
        for _ in range(4):
            response = self.client.post('/api/generate', data=json.dumps({'profile': profile, 'role': role}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/generation-quota').json()['remaining'], 0)
        response = self.client.post('/api/generate', data=json.dumps({'profile': profile, 'role': role}), content_type='application/json')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(DailyAIUsage.objects.get().generations, 4)


class OptionalAPIKeyTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='key-test'))

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-server-test', 'HIREATIONSHIP_ALLOW_SHARED_CLAUDE':'1'})
    def test_free_mode_is_default_even_with_server_key(self):
        self.assertEqual(self.client.get('/api/status').json()['mode'], 'demo')
        self.assertEqual(self.client.get('/api/status', HTTP_X_AI_MODE='server').json()['mode'], 'claude')

    def test_personal_key_does_not_persist_or_cross_requests(self):
        response = self.client.get('/api/status', HTTP_X_AI_MODE='personal', HTTP_X_ANTHROPIC_KEY='sk-ant-personal-test')
        self.assertEqual(response.json()['mode'], 'claude')
        self.assertNotIn('sk-ant-personal-test', response.content.decode())
        self.assertEqual(self.client.get('/api/status').json()['mode'], 'demo')
        self.assertNotIn('sk-ant-personal-test', json.dumps(self.client.get('/api/workspace').json()))

    def test_invalid_personal_key_is_rejected(self):
        response = self.client.get('/api/status', HTTP_X_AI_MODE='personal', HTTP_X_ANTHROPIC_KEY='invalid')
        self.assertEqual(response.status_code, 400)

    def test_local_screening_excludes_complex_or_unclear_requirements(self):
        profile = {'gradYear': 2027, 'skills': ['python'], 'experiences': []}
        jobs = [{'id': str(i), 'title': title, 'summary': summary} for i, (title, summary) in enumerate([
            ('Graduate developer', 'Python required. Must have security clearance.'),
            ('Graduate developer', 'Python required. Must have an unknown professional certificate.'),
            ('Graduate developer', 'Python required. Three years experience required.'),
            ('Graduate developer', 'Python required. SQL preferred.'),
        ])]
        matches = [a for a in demo.assess_live_jobs(profile, jobs) if a['eligible']]
        self.assertEqual([a['id'] for a in matches], ['3'])


class OpenRegistrationTests(TestCase):
    def test_registration_without_invite_creates_account_and_signs_in(self):
        self.assertContains(self.client.get('/register/'), 'Create free account')
        response = self.client.post('/register/', {'username':'new-person','password1':'A-real-test-pass-928!', 'password2':'A-real-test-pass-928!'})
        self.assertRedirects(response, '/')
        self.assertTrue(get_user_model().objects.filter(username='new-person').exists())
        self.assertContains(self.client.get('/'), 'Your base CV')

    def test_old_invite_urls_still_show_registration(self):
        self.assertContains(self.client.get('/register/?invite=old-or-expired'), 'Create free account')

    def test_duplicate_username_and_password_mismatch_are_rejected(self):
        get_user_model().objects.create_user(username='taken')
        response = self.client.post('/register/', {'username':'taken','password1':'first','password2':'different'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_still_required_and_workspaces_are_separate(self):
        self.assertEqual(self.client.get('/api/workspace').status_code, 401)
        first=get_user_model().objects.create_user(username='first')
        second=get_user_model().objects.create_user(username='second')
        self.client.force_login(first)
        self.client.post('/api/workspace', data=json.dumps({'cv':'private CV'}), content_type='application/json')
        self.client.force_login(second)
        self.assertEqual(self.client.get('/api/workspace').json()['data'], {})

    @patch.dict('os.environ', {'ADZUNA_APP_ID':'test','ADZUNA_APP_KEY':'test','HIREATIONSHIP_DAILY_JOB_SEARCH_LIMIT':'2'})
    @patch('matching.views.requests.get')
    def test_live_search_limit_is_per_account_and_blocks_upstream_calls(self, fetch):
        fetch.return_value=Mock(json=lambda:{'results':[], 'count':0})
        user=get_user_model().objects.create_user(username='searcher')
        self.client.force_login(user)
        body=json.dumps({'profile':{'gradYear':2027}})
        for _ in range(2):
            self.assertEqual(self.client.post('/api/live-jobs',data=body,content_type='application/json').status_code,200)
        self.assertEqual(self.client.post('/api/live-jobs',data=body,content_type='application/json').status_code,429)
        self.assertEqual(fetch.call_count,2)
        self.client.force_login(get_user_model().objects.create_user(username='another-searcher'))
        self.assertEqual(self.client.post('/api/live-jobs',data=body,content_type='application/json').status_code,200)


class AdvertReaderTests(SimpleTestCase):
    def test_extracts_structured_job_description(self):
        from .job_details import extract_description
        description='<h2>Requirements</h2><p>Python and Git skills required. A 2:1 degree in computer science is required.</p><p>'+'Work on useful software with our graduate engineering team. '*5+'</p>'
        html='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':[{'@type':'JobPosting','title':'Graduate developer','description':description}]})+'</script>'
        text,source=extract_description(html,'Graduate developer')
        self.assertIn('Python and Git skills required',text)
        self.assertNotIn('<p>',text)
        self.assertEqual(source,'structured job description')

    def test_does_not_treat_bot_challenge_as_job_description(self):
        from .job_details import extract_description
        with self.assertRaises(ValueError):
            extract_description('<main>Verify you are human</main>','Graduate developer')

    @patch('matching.job_details.socket.getaddrinfo')
    def test_blocks_private_and_mixed_dns_addresses(self, dns):
        from .job_details import public_target
        for addresses in [['127.0.0.1'],['169.254.169.254'],['::1'],['93.184.216.34','10.0.0.1']]:
            dns.return_value=[(None,None,None,None,(ip,443)) for ip in addresses]
            with self.subTest(addresses=addresses), self.assertRaises(ValueError): public_target('https://example.com/job')
        for url in ['http://example.com/job','https://example.com:8443/job','https://user:pass@example.com/job']:
            with self.subTest(url=url), self.assertRaises(ValueError): public_target(url)

    @patch('matching.job_details.public_target')
    @patch('matching.job_details.PinnedHTTPSConnection')
    def test_redirect_target_is_revalidated(self, connection, target):
        from .job_details import fetch_page
        from urllib.parse import urlsplit
        target.side_effect=[(urlsplit('https://example.com/job'),'93.184.216.34'),ValueError('private target')]
        response=Mock(status=302)
        response.getheader.return_value='https://127.0.0.1/private'
        connection.return_value.getresponse.return_value=response
        with self.assertRaises(ValueError):fetch_page('https://example.com/job')
        self.assertEqual(connection.call_count,1)


class FullAdvertEndpointTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client.force_login(get_user_model().objects.create_user(username='reader'))
        self.role={'id':'adzuna-test','title':'Graduate developer','applyUrl':'https://example.com/job'}
        self.profile={'gradYear':2027,'classification':'2:1','skills':['python','git'],'experiences':[],'subjectTags':['computer-science']}
        self.text='Requirements: Python and Git required. A 2:1 degree in computer science is required.\n'+ 'Build software for customers and collaborate with our engineering team. '*4

    @patch('matching.job_details.read_advert')
    def test_reads_and_matches_without_paid_ai_or_generation_use(self, read):
        read.return_value={'text':self.text,'source':'structured job description','url':'https://example.com/job'}
        response=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['outcome'],'matched')
        usage=DailyAIUsage.objects.get()
        self.assertEqual((usage.generations,usage.job_searches),(0,1))

    @patch('matching.job_details.read_advert')
    def test_paste_fallback_works_without_fetching_or_using_search_quota(self, read):
        response=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile,'text':self.text}),content_type='application/json')
        self.assertEqual(response.json()['outcome'],'matched')
        self.assertFalse(DailyAIUsage.objects.exists())
        read.assert_not_called()

    @patch('matching.job_details.read_advert',side_effect=ValueError('blocked'))
    def test_blocked_site_offers_paste_fallback(self, read):
        response=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile}),content_type='application/json')
        self.assertEqual(response.status_code,400)
        self.assertIn('paste',response.json()['error'])

    def test_full_text_does_not_confuse_company_history_or_mentors_with_requirements(self):
        text='Founded in 2016, our company has 20 years of history. Work with senior mentors.\nRequirements: Python and Git skills required.\n'+ 'Our graduate programme provides mentoring and training. '*4
        response=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile,'text':text}),content_type='application/json')
        self.assertEqual(response.json()['outcome'],'matched')
        self.assertEqual(response.json()['supportedSkills'],['python','git'])

    @patch.dict('os.environ', {'ADZUNA_APP_ID':'test','ADZUNA_APP_KEY':'test'})
    @patch('matching.views.requests.get')
    def test_live_search_pages_beyond_first_fifty(self, fetch):
        jobs=[{'id':str(i),'title':'Graduate developer','description':'Python required.', 'redirect_url':'https://example.com/job'} for i in range(50)]
        fetch.return_value=Mock(json=lambda:{'results':jobs,'count':125})
        response=self.client.post('/api/live-jobs',data=json.dumps({'profile':self.profile,'page':2}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertTrue(fetch.call_args.args[0].endswith('/search/2'))
        self.assertEqual(response.json()['nextPage'],3)
        fetch.return_value=Mock(json=lambda:{'results':jobs[:25],'count':125})
        response=self.client.post('/api/live-jobs',data=json.dumps({'profile':self.profile,'page':3}),content_type='application/json')
        self.assertIsNone(response.json()['nextPage'])
        self.assertEqual(response.json()['page'],3)

    @patch.dict('os.environ', {'ADZUNA_APP_ID':'test','ADZUNA_APP_KEY':'test'})
    @patch('matching.views.requests.get')
    def test_fourteen_results_have_no_extra_page(self, fetch):
        jobs=[{'id':str(i),'title':'Graduate developer','description':'Python required.', 'redirect_url':'https://example.com/job'} for i in range(14)]
        fetch.return_value=Mock(json=lambda:{'results':jobs,'count':14})
        response=self.client.post('/api/live-jobs',data=json.dumps({'profile':self.profile}),content_type='application/json')
        self.assertIsNone(response.json()['nextPage'])
        response=self.client.post('/api/live-jobs',data=json.dumps({'profile':self.profile,'page':-1}),content_type='application/json')
        self.assertEqual(response.status_code,400)


class SearchPreferencesTests(SimpleTestCase):
    def test_multiple_interests_and_locations_are_separate_queries(self):
        from .search_preferences import search_plan
        profile={'gradYear':2027,'preferences':{'interests':['software','data-science'],'locations':['London','Manchester'],'locationMode':'locations','opportunityType':'grad'}}
        plans=search_plan(profile)
        self.assertEqual(plans,[{'what':'graduate software','where':'London'},{'what':'graduate software','where':'Manchester'},{'what':'graduate data','where':'London'},{'what':'graduate data','where':'Manchester'}])

    def test_remote_and_uk_wide_do_not_infer_cv_address(self):
        from .search_preferences import search_plan
        profile={'gradYear':2027,'address':'London','preferences':{'interests':['software'],'locationMode':'remote','opportunityType':'internship'}}
        self.assertEqual(search_plan(profile),[{'what':'internship software remote','where':''}])
        profile['preferences']['locationMode']='uk'
        self.assertEqual(search_plan(profile),[{'what':'internship software','where':''}])

    def test_invalid_or_unbounded_preferences_rejected(self):
        from .search_preferences import search_plan
        for preferences in [{'interests':['unknown']},{'locationMode':'locations'}, {'locations':['London','Bristol','Leeds']}]:
            with self.subTest(preferences=preferences),self.assertRaises(ValueError):
                search_plan({'gradYear':2027,'preferences':preferences})


class PreferenceSearchEndpointTests(TestCase):
    @patch.dict('os.environ', {'ADZUNA_APP_ID':'test','ADZUNA_APP_KEY':'test'})
    @patch('matching.views.requests.get')
    def test_combines_queries_deduplicates_and_accounts_for_shared_usage(self, fetch):
        self.client.force_login(get_user_model().objects.create_user(username='preferences'))
        job={'id':'same','title':'Graduate developer','description':'Python required.','redirect_url':'https://example.com/job'}
        fetch.return_value=Mock(json=lambda:{'results':[job],'count':1})
        profile={'gradYear':2027,'skills':['python'],'preferences':{'interests':['software'],'locations':['London','Bristol'],'locationMode':'locations','opportunityType':'grad'}}
        response=self.client.post('/api/live-jobs',data=json.dumps({'profile':profile}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['queryCount'],2)
        self.assertEqual(len(response.json()['jobs']),1)
        self.assertEqual(DailyAIUsage.objects.get().job_searches,2)
        self.assertEqual([call.kwargs['params']['where'] for call in fetch.call_args_list],['London','Bristol'])
        self.assertTrue(all(call.kwargs['params']['results_per_page']==25 for call in fetch.call_args_list))

    def test_preferences_are_saved_in_private_profile(self):
        self.client.force_login(get_user_model().objects.create_user(username='saved-preferences'))
        profile={'preferences':{'interests':['research'],'locationMode':'uk','source':'live'}}
        response=self.client.post('/api/workspace',data=json.dumps({'profile':profile}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.get('/api/workspace').json()['data']['profile'],profile)


class AdvertCacheTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client.force_login(get_user_model().objects.create_user(username='cached-reader'))
        self.role={'id':'adzuna-cache','title':'Graduate developer','applyUrl':'https://example.com/cached-job'}
        self.profile={'gradYear':2027,'skills':['python','git']}
        self.text='Python and Git skills required. '+ 'Build useful tools for our customers in a graduate software team. '*4

    @patch('matching.job_details.read_advert')
    def test_cached_text_reused_but_profile_rechecked_without_extra_search_use(self, read):
        read.return_value={'text':self.text,'source':'structured job description','url':self.role['applyUrl']}
        payload={'role':self.role,'profile':self.profile}
        first=self.client.post('/api/job-details',data=json.dumps(payload),content_type='application/json')
        self.assertEqual(first.json()['outcome'],'matched')
        payload['profile']={**self.profile,'skills':['python']}
        second=self.client.post('/api/job-details',data=json.dumps(payload),content_type='application/json')
        self.assertEqual(second.json()['outcome'],'ineligible')
        self.assertEqual(read.call_count,1)
        self.assertEqual(DailyAIUsage.objects.get().job_searches,1)
        self.assertEqual(DailyAIUsage.objects.get().generations,0)

    @patch('matching.job_details.read_advert',side_effect=ValueError('blocked'))
    def test_blocked_site_is_cached_briefly_to_avoid_repeated_fetches(self, read):
        for _ in range(2):
            result=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile}),content_type='application/json')
            self.assertEqual(result.status_code,400)
        self.assertEqual(read.call_count,1)
        self.assertEqual(DailyAIUsage.objects.get().job_searches,1)


class RestrictedHostingTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client.force_login(get_user_model().objects.create_user(username='restricted-host'))
        self.role={'id':'adzuna-restricted','title':'Graduate developer','applyUrl':'https://example.com/restricted-job'}
        self.profile={'gradYear':2027,'skills':['python']}

    @patch.dict('os.environ', {'http_proxy':'http://proxy.server:3128','HIREATIONSHIP_FULL_ADVERT_FETCH_ENABLED':'auto'})
    @patch('matching.job_details.read_advert')
    def test_restricted_host_does_not_spend_allowance_on_unavailable_reads(self, read):
        response=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile}),content_type='application/json')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['code'],'hosting_network_restricted')
        self.assertFalse(DailyAIUsage.objects.exists())
        read.assert_not_called()
        self.assertFalse(self.client.get('/api/status').json()['fullAdvertReadsAvailable'])

    @patch.dict('os.environ', {'HIREATIONSHIP_FULL_ADVERT_FETCH_ENABLED':'0'})
    @patch('matching.job_details.read_advert')
    def test_pasted_text_still_checked_when_host_cannot_fetch(self, read):
        text='Python skills required. '+ 'Build software with our graduate development team and learn through projects. '*4
        response=self.client.post('/api/job-details',data=json.dumps({'role':self.role,'profile':self.profile,'text':text}),content_type='application/json')
        self.assertEqual(response.json()['outcome'],'matched')
        self.assertFalse(DailyAIUsage.objects.exists())
        read.assert_not_called()

    @patch.dict('os.environ', {'HIREATIONSHIP_FULL_ADVERT_FETCH_ENABLED':'1','http_proxy':'http://proxy.server:3128'})
    def test_explicit_host_configuration_is_respected(self):
        self.assertTrue(self.client.get('/api/status').json()['fullAdvertReadsAvailable'])


class DeploymentHostTests(SimpleTestCase):
    def test_exact_vercel_preview_branch_and_production_hosts_are_allowed(self):
        from config.hosting import host_settings
        from django.test import override_settings
        env={'DJANGO_ALLOWED_HOSTS':'itkara.pythonanywhere.com','VERCEL_URL':'claude-builder-hackathon-bunssce69-itkara.vercel.app','VERCEL_BRANCH_URL':'claude-builder-git-main-itkara.vercel.app','VERCEL_PROJECT_PRODUCTION_URL':'hireationship.example.com'}
        hosts,origins=host_settings(env)
        for host in [env['VERCEL_URL'],env['VERCEL_BRANCH_URL'],env['VERCEL_PROJECT_PRODUCTION_URL']]:
            self.assertIn(host,hosts)
            self.assertIn('https://'+host,origins)
            with override_settings(ALLOWED_HOSTS=hosts):
                self.assertEqual(RequestFactory().get('/',HTTP_HOST=host).get_host(),host)
        self.assertIn('itkara.pythonanywhere.com',hosts)
        self.assertNotIn('.vercel.app',hosts)
        self.assertNotIn('*',hosts)

    def test_unrelated_and_invalid_hosts_remain_rejected(self):
        from config.hosting import host_settings
        from django.test import override_settings
        from django.core.exceptions import DisallowedHost
        hosts,origins=host_settings({'VERCEL_URL':'https://bad.vercel.app/path','VERCEL_BRANCH_URL':'*.vercel.app'})
        self.assertNotIn('https://bad.vercel.app/path',hosts)
        with override_settings(ALLOWED_HOSTS=hosts),self.assertRaises(DisallowedHost):
            RequestFactory().get('/',HTTP_HOST='unrelated.vercel.app').get_host()
        self.assertEqual(origins,['https://itkara.pythonanywhere.com'])

    def test_csrf_origin_matches_allowed_vercel_host(self):
        from config.hosting import host_settings
        from django.middleware.csrf import CsrfViewMiddleware
        from django.test import override_settings
        host='claude-builder-hackathon-bunssce69-itkara.vercel.app'
        hosts,origins=host_settings({'VERCEL_URL':host})
        request=RequestFactory().post('/login/',HTTP_HOST=host,HTTP_ORIGIN='https://'+host,secure=True)
        with override_settings(ALLOWED_HOSTS=hosts,CSRF_TRUSTED_ORIGINS=origins):
            self.assertTrue(CsrfViewMiddleware(lambda req:None)._origin_verified(request))
