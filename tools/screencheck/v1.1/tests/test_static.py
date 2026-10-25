"""Purely offline preflight tests. Does not execute Windows C# or send email."""
import pathlib
import re
import unittest
from collections import Counter
try:
    from pygments import lex
    from pygments.lexers import CSharpLexer
    from pygments.token import Token
except ImportError:
    lex = CSharpLexer = Token = None

BASE = pathlib.Path(__file__).resolve().parents[1]
SRC = (BASE / 'MiamedScreenCheckV11.cs').read_text(encoding='utf-8')
FIXTURE = (BASE / 'tests/ProbeTestsV11.cs').read_text(encoding='utf-8')
README = (BASE / 'README.txt').read_text(encoding='utf-8')

class PreflightTests(unittest.TestCase):
    def test_files_present(self):
        for p in ('MiamedScreenCheckV11.cs','BASLAT.cmd','build.ps1','Windows_Test.ps1','README.txt','tests/ProbeTestsV11.cs'):
            self.assertTrue((BASE/p).is_file(), p)

    def test_code_structure(self):
        if CSharpLexer is None:
            self.skipTest('Pygments unavailable')
        for path, source in [('main',SRC),('synthetic fixture',FIXTURE)]:
            stack=[]
            pairs={'}':'{',')':'(',']':'['}
            for category,value in lex(source, CSharpLexer()):
                if category in Token.Comment or category in Token.Literal.String: continue
                for ch in value:
                    if ch in '{([': stack.append(ch)
                    if ch in '})]':
                        self.assertTrue(stack, f'{path}: closing bracket without opener')
                        self.assertEqual(stack.pop(),pairs[ch],f'{path}: unbalanced C# brackets')
            self.assertFalse(stack,f'{path}: unterminated bracket')

    def test_no_write_access_to_miamed(self):
        for forbidden in ('SetValue(', 'SetFocus(', 'SendKeys.', 'SendInput(', 'SendMessage(', 'mouse_event(', 'keybd_event(', 'InvokePattern', 'GetText(', 'Current.Value', 'Current.AutomationId', 'GetCurrentPattern(TextPattern.Pattern)', 'WebClient('):
            self.assertNotIn(forbidden, SRC, forbidden)

    def test_fixed_label_classification_and_privacy(self):
        self.assertIn('skipName=current.ControlType==ControlType.Edit', SRC)
        self.assertIn('current.IsPassword', SRC)
        self.assertIn('label_hint=skipName ? "not_read" : Hint(current.Name)', SRC)
        self.assertNotIn('[DataMember] public string name;', SRC)
        self.assertNotIn('[DataMember] public string value;', SRC)
        self.assertNotIn('[DataMember] public string automation_id;', SRC)
        self.assertNotIn('ControlViewWalker.GetNextSibling',FIXTURE)  # fixture must not alter app

    def test_bounded_walk(self):
        for constraint in ('nodes.Count>=3500','watch.ElapsedMilliseconds>20000','tuple.Item3>=28','children.Count<1000'):
            self.assertIn(constraint,SRC)
        for reason in ('node_limit','time_limit','depth_limit','children_limit'):
            self.assertIn('"'+reason+'"',SRC)

    def test_email_outbound_and_opt_in(self):
        for required in ('new SmtpClient("smtp.gmail.com",587)', 'smtp.EnableSsl=true', 'smtp.UseDefaultCredentials=false',
                         'ProtectedData.Protect', 'DataProtectionScope.CurrentUser','permit.Checked','new MailMessage(config[0],config[0])','MailConfig.Disable()'):
            self.assertIn(required,SRC)
        self.assertEqual(SRC.count('smtp.Send(message)'),1)
        self.assertIn('if(cfg==null)result=',SRC)
        self.assertIn('if(!permit.Checked)',SRC)
        self.assertIn('File.WriteAllText(savedPath,json',SRC)
        self.assertIn('scan_scope="full_window"',SRC)
        self.assertNotIn('password=', README.lower())

    def test_actual_windows_acceptance_fixture_available(self):
        for required in ('missing_target_status','privacy_exported_','source_modified','editable_metadata','selected_section','truncation_reason'):
            self.assertIn(required,FIXTURE)
        self.assertIn("'tests\\ProbeTestsV11.cs'",(BASE/'Windows_Test.ps1').read_text())

    def test_document_limits_truthful(self):
        for claim in ('gerçek SMTP', 'Kurum', 'Gmail', 'gerçek hasta', 'Windows_Test.ps1'):
            self.assertIn(claim.lower(), README.lower())

if __name__=='__main__':unittest.main(verbosity=2)
