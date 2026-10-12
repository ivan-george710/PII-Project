"""Generate public synthetic labels; independent of detector output."""
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]


def build():
    cases = []
    def add(category, text, positives=(), negatives=(), notes=""):
        def spans(values):
            result = []
            for value, entity in values:
                start = 0
                while (start := text.find(value, start)) >= 0:
                    result.append(dict(start=start, end=start+len(value), entity_type=entity))
                    start += len(value)
            return result
        cases.append(dict(id=f"S{len(cases)+1:04}", category=category, text=text,
                          expected=spans(positives), non_pii=spans(negatives), notes=notes))
    # Names are invented combinations; contact values use reserved example domains
    # and North American fictional 555-01xx telephone ranges.
    first = ['John', 'Amelia', 'Oliver', 'Nora', 'Ethan', 'Clara', 'Felix', 'Iris', 'Leo', 'Maya',
             'Ada', 'Theo', 'Elena', 'Hugo', 'Lena', 'Oscar', 'Vera', 'Miles', 'Ruby', 'Simon']
    last = ['Smith', 'Alder', 'Brook', 'Vale', 'Reed', 'Finch', 'Marsh', 'Rowan', 'Cedar', 'Stone',
            'Briar', 'West', 'Field', 'Lake', 'Grove', 'Ash', 'Dale', 'Elm', 'Hart', 'Wren']
    for i, (a, b) in enumerate(zip(first, last)):
        name = a+' '+b
        email = f'{a.lower()}.{b.lower()}@example.com'
        emp = f'EMP-{12000+i:05}'
        phone = f'+1 (212) 555-{100+i:04}'
        add('person', 'Policy owner: '+name+'.', [(name,'PERSON')])
        add('header', name+'\nQuarterly governance report', [(name,'PERSON')])
        add('title_name', 'Chief Risk Officer: '+name+'.', [(name,'PERSON')])
        add('email', 'Contact: '+email, [(email,'EMAIL_ADDRESS')])
        add('phone', 'Telephone: '+phone, [(phone,'PHONE_NUMBER')])
        add('employee', 'Employee identifier: '+emp, [(emp,'EMPLOYEE_ID')])
        add('table', 'Owner | Employee | Email\n'+name+' | '+emp+' | '+email,
            [(name,'PERSON'),(emp,'EMPLOYEE_ID'),(email,'EMAIL_ADDRESS')])
        add('adjacent_email', name+' <'+email+'>', [(name,'PERSON'),(email,'EMAIL_ADDRESS')])
        add('duplicate_context', f'Owner: {name}. Reviewed by: {name}.', [(name,'PERSON')])
        add('ocr_name', a+b+' is the policy author.', [(a+b,'PERSON')],
            notes='Synthetic OCR concatenation; exact source span required, no invented spaces.')
        add('malformed_employee', f'Release code EMP-{12000+i}X; employee field unavailable.',
            negatives=[(f'EMP-{12000+i}X','EMPLOYEE_ID')])
        add('malformed_email', f'Contact field: {a.lower()}..{b.lower()}@example.com',
            negatives=[(f'{a.lower()}..{b.lower()}@example.com','EMAIL_ADDRESS')],
            notes='Consecutive dots invalidate the unquoted local part; substring is not a gold match.')
        add('numeric_business', f'Revenue amount: {2125550100+i} dollars; growth {i+1}%.',
            negatives=[(str(2125550100+i),'PHONE_NUMBER')])
        add('account', f'Bank account number: {73000000+i}', [(str(73000000+i),'US_BANK_NUMBER')],
            notes='Explicit bank account context supports policy PII; may need review.')
        add('code', f'Internal project code ZX-{2125550100+i}; Account {12345+i}.',
            negatives=[(str(2125550100+i),'PHONE_NUMBER'),(str(12345+i),'US_BANK_NUMBER')])
    negatives = [
        ('department','Risk Management'),('department','Operations Team'),
        ('committee','Smith Risk Committee'),('organization','Alder Financial Group'),
        ('organization','Brook Holdings Limited'),('role','Chief Compliance Officer'),
        ('business','Capital Allocation'),('business','Credit Exposure'),
        ('project','Project Silver Harbor'),('abbreviation','RCSA'),
        ('abbreviation','NED'),('ambiguous_capitals','Blue Horizon'),
        ('footer','Document Control Department'),('address','100 Example Avenue'),
        ('date','2025-04-12'),('numeric_business','123456789'),
        ('malformed_email','person@'),('malformed_employee','EMP-1234'),
        ('malformed_employee','EMP-123456'),('code','POLICY-12345')]
    for i in range(5):
        for category, value in negatives:
            add(category, f'Internal governance record {i+1}: {value}.',
                negatives=[(value,'PERSON' if category in {'department','committee','organization','role','business','project','ambiguous_capitals','footer'} else 'NON_PII')],
                notes='Addresses/dates are outside current redaction policy. Blue Horizon denotes a project here.')
    for i in range(20):
        ssn = f'219-{30+i:02}-{1000+i:04}'
        add('ssn', 'Synthetic payroll SSN: '+ssn, [(ssn,'US_SSN')],
            notes='Invented test-only digits, not sourced from a person or real document.')
    rng = random.Random(10010)
    for category in sorted({c['category'] for c in cases}):
        group = [c for c in cases if c['category']==category]
        rng.shuffle(group)
        cut = round(len(group)*.7)
        for i,c in enumerate(group): c['split'] = 'development' if i<cut else 'heldout'
    return dict(version='synthetic-1', seed=10010, matching='exact offsets and entity, unique predictions',
                cases=cases)


if __name__ == '__main__':
    destination = ROOT/'tests/data/detector_evaluation.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(build(), indent=2), encoding='utf-8')
    print('Created 420 synthetic labeled cases.')
