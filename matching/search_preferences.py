"""Translate reviewed CV preferences into bounded live-search queries."""
from .demo import demo_families
from .matcher import stage_for

ROLE_TERMS={'software':'software','data-science':'data','engineering':'engineer','consulting':'consultant','quant-finance':'finance','research':'research','policy-science-comms':'communications','patent-law':'patent','teaching':'teaching'}
TYPE_TERMS={'grad':'graduate','internship':'internship','placement':'placement','insight':'insight'}


def search_plan(profile):
    preferences=profile.get('preferences') or {}
    if not isinstance(preferences,dict):raise ValueError('Invalid search preferences.')
    interests=preferences.get('interests') or [family['id'] for family in demo_families(profile)[:3]]
    if not isinstance(interests,list) or len(interests)>3 or any(item not in ROLE_TERMS for item in interests):
        raise ValueError('Choose up to three role interests.')
    kind=preferences.get('opportunityType','auto')
    if kind=='auto':kind='grad' if stage_for(profile['gradYear'])=='final' else 'internship' if stage_for(profile['gradYear'])=='penultimate' else 'insight'
    if kind not in TYPE_TERMS:raise ValueError('Choose an opportunity type.')
    mode=preferences.get('locationMode','uk')
    locations=preferences.get('locations') or []
    if mode not in ('uk','locations','remote') or not isinstance(locations,list) or len(locations)>2 or any(not isinstance(item,str) or not item.strip() or len(item)>90 for item in locations):
        raise ValueError('Choose UK-wide, remote, or up to two locations.')
    if mode=='locations' and not locations:raise ValueError('Add at least one preferred location.')
    places=list(dict.fromkeys(item.strip() for item in locations)) if mode=='locations' else ['']
    roles=list(dict.fromkeys(interests)) or ['']
    return [{'what':' '.join(filter(None,[TYPE_TERMS[kind],ROLE_TERMS.get(role,''),'remote' if mode=='remote' else ''])), 'where':place} for role in roles for place in places]
