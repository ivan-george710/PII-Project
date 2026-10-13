from presidio_analyzer import Pattern, PatternRecognizer, EntityRecognizer


class EmployeeIdRecognizer(PatternRecognizer):
    """
    Detects Cadence employee identifiers such as:
    EMP-38104
    EMP-40522
    """

    PATTERNS = [
        Pattern(
            name="cadence_employee_id",
            regex=r"(?<![\w-])EMP-[0-9]{4,8}(?![\w-])",
            score=0.95,
        )
    ]

    CONTEXT = [
        "employee",
        "employee id",
        "employee identifier",
        "staff",
        "personnel",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="EMPLOYEE_ID",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
            name="CadenceEmployeeIdRecognizer",
            global_regex_flags=0,  # Documented uppercase EMP- plus four to eight digits.
        )


class SensitiveFieldRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(supported_entity='CREDENTIAL',name='SensitiveFieldRecognizer',
            patterns=[Pattern('labeled_secret',r'password\s*[:=]\s*\S+',.95)])

    def analyze(self,text,entities,nlp_artifacts=None):
        import re
        from presidio_analyzer import RecognizerResult
        pattern=r'(?:password(?:\s+for\s+[^:\n]{1,60})?|passwd|passcode|api[ _-]?key|access[ _-]?token|secret|username)(?:\s*[:=]\s*|\s*\n\s*)([^\s,;]+)'
        values=[]
        for match in re.finditer(pattern,text,re.I):
            if ':' not in match.group(0) and '=' not in match.group(0) and match.group(1).lower() in {'login','submit','continue','password','username'}:
                continue
            values.append(RecognizerResult('CREDENTIAL',match.start(1),match.end(1),.95,
                recognition_metadata={'recognizer_name':self.name}))
        for heading in re.finditer(r'(?im)^(?:accepted\s+)?usernames(?:\s+are)?\s*:\s*\n',text):
            cursor=heading.end()
            for line in text[cursor:].splitlines(keepends=True)[:20]:
                value=line.strip()
                if not value or ':' in value or len(value.split())!=1:break
                start=cursor+len(line)-len(line.lstrip())
                values.append(RecognizerResult('CREDENTIAL',start,start+len(value),.95,
                    recognition_metadata={'recognizer_name':self.name}))
                cursor+=len(line)
        return values


class IntroductionRecognizer:
    @staticmethod
    def candidates(text,analyzer):
        from spacy.matcher import Matcher
        from presidio_analyzer import RecognizerResult
        nlp=analyzer.nlp_engine.nlp['en'];doc=nlp.make_doc(text)
        matcher=Matcher(nlp.vocab);value={'IS_ALPHA':True,'LENGTH':{'>=':1}}
        matcher.add('INTRO',[
            [{'LOWER':'my'},{'LOWER':'name'},{'LOWER':'is'},value],
            [{'LOWER':'name'},{'LOWER':'is'},value],
            [{'LOWER':'i'},{'LOWER':'am'},value],
            [{'LOWER':'i'},{'LOWER':{'IN':["'m","’m",'m']}},value],
            [{'LOWER':'im'},value],
        ])
        exclude={'a','an','the','fine','okay','ok','happy','here','ready','sorry','trying','looking','going','fictional','employee'}
        for _,start,end in matcher(doc):
            token=doc[end-1]
            if token.lower_ not in exclude:
                yield RecognizerResult('PERSON',token.idx,token.idx+len(token),.95,
                    recognition_metadata={'recognizer_name':'IntroductionRecognizer'})


class MailboxRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(supported_entity='EMAIL_ADDRESS',name='MailboxRecognizer',
            patterns=[Pattern('mailbox',r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",.95)])


class LabeledPIIRecognizer(EntityRecognizer):
    """Explicit document fields cover values missed by generic NER."""
    FIELDS = [
        ('PERSON',r'(?:name|author|policy\s*owner|prepared\s*by)'),
        ('ADDRESS', r'(?:home\s*address|residential\s*address|address)'),
        ('DATE_OF_BIRTH', r'(?:dob|date\s*of\s*birth|birth\s*date)'),
        ('US_PASSPORT',r'(?:passport(?:\s*(?:number|no))?)'),
        ('US_DRIVER_LICENSE',r'(?:driver(?:s|\x27s)?\s*licen[cs]e(?:\s*(?:number|no))?)'),
        ('US_BANK_NUMBER',r'(?:bank\s*account(?:\s*(?:number|no))?)'),
        ('MEDICAL_LICENSE',r'(?:dea|medical\s*license)'),
        ('MAC_ADDRESS',r'(?:mac(?:\s*address)?)'),
    ]
    def __init__(self):
        super().__init__(supported_entities=[e for e,_ in self.FIELDS],name='LabeledPIIRecognizer')

    def analyze(self,text,entities,nlp_artifacts=None):
        import re
        from presidio_analyzer import RecognizerResult
        values=[]
        for entity,label in self.FIELDS:
            for match in re.finditer(r'(?i)\b'+label+r'\s*[:=]\s*([^\n;]+)',text):
                value=match.group(1).rstrip()
                if value:
                    values.append(RecognizerResult(entity,match.start(1),match.start(1)+len(value),.95,
                        recognition_metadata={'recognizer_name':self.name}))
        return values
