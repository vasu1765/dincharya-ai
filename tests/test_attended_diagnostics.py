import io
import unittest
from contextlib import redirect_stderr
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

from dincharya.attended_operator import Telegram, operation_diagnostic, signed_route


class OperationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.bot = Telegram(self.client, "91002:"+"t"*32,
                            SimpleNamespace(bot=91002, owner=91001, bot_username="PrivateTestBot"))
        self.me = {"id":91002, "is_bot":True, "username":"PrivateTestBot"}
        self.secret = "https://fixture.invalid/private-token?chat=91001 private-response-body"

    def operations(self, submit):
        return [("getMe", self.bot.me), ("getUpdates", lambda:self.bot.poll(1234)),
                ("sendMessage", lambda:self.bot.send(chat_id=91001,text=self.secret)),
                ("signed_relay", lambda:submit({"private":self.secret}, self.secret))]

    def diagnostic(self, operation, action, expected=None):
        out=io.StringIO()
        with redirect_stderr(out), patch("time.monotonic_ns",side_effect=[500000000,1033000000]):
            if expected is None:
                action()
            else:
                with self.assertRaises(type(expected)) as caught:
                    action()
                self.assertIs(caught.exception,expected)
        return out.getvalue()

    def test_timeout_localized_without_leaking_exception_or_retrying(self):
        with signed_route("s"*32,self.client) as submit:
            for op,action in self.operations(submit):
                with self.subTest(op=op):
                    error=httpx.ReadTimeout(self.secret,request=httpx.Request("POST","https://fixture.invalid/token"))
                    self.client.post.side_effect=error
                    self.client.post.reset_mock()
                    self.assertEqual(self.diagnostic(op,action,error),
                                     f"operation={op} elapsed_ms=533 exception=ReadTimeout\n")
                    self.client.post.assert_called_once()

    def test_success_fields_only(self):
        import urllib.request
        original=self.client.post
        def relay_post(url,json,headers):
            from dincharya.lunar_service import canonical
            request=urllib.request.Request("http://127.0.0.1:8080/lunar",
                      data=canonical(json).encode(),headers=headers)
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=2) as response:
                return httpx.Response(response.status,json={"status":"accepted"},
                                      request=httpx.Request("POST","http://fixture.invalid"))
        with signed_route("s"*32,self.client) as submit:
            for op,action in self.operations(submit):
                if op=="signed_relay":
                    from dincharya.lunar_service import sign
                    value={"private":self.secret}
                    self.client.post.side_effect=relay_post
                    action=lambda:submit(value,sign("s"*32,"command",value))
                else:
                    original.return_value.json.return_value={"ok":True,"result":self.me}
                self.assertEqual(self.diagnostic(op,action),f"operation={op} elapsed_ms=533 exception=none\n")

    def test_unknown_exception_name_and_message_are_redacted(self):
        error=type("PrivateName91001",(Exception,),{})(self.secret)
        self.client.post.side_effect=error
        self.assertEqual(self.diagnostic("getMe",self.bot.me,error),
                         "operation=getMe elapsed_ms=533 exception=Exception\n")

    def test_identity_validation_is_inside_operation(self):
        self.client.post.return_value.json.return_value={"ok":True,"result":{**self.me,"username":self.secret}}
        out=io.StringIO()
        with redirect_stderr(out),self.assertRaises(ValueError):
            self.bot.me()
        self.assertRegex(out.getvalue(),r"\Aoperation=getMe elapsed_ms=\d+ exception=ValueError\n\Z")

    def test_untrusted_operation_rejected_without_logging(self):
        out=io.StringIO()
        with redirect_stderr(out),self.assertRaises(ValueError),operation_diagnostic(self.secret):
            self.fail("Unapproved operation ran")
        self.assertEqual(out.getvalue(),"")

    def test_output_failure_preserves_original_failure(self):
        error=httpx.WriteTimeout(self.secret)
        self.client.post.side_effect=error
        sink=Mock()
        sink.write.side_effect=BrokenPipeError
        with redirect_stderr(sink),self.assertRaises(httpx.WriteTimeout) as caught:
            self.bot.send(chat_id=91001,text=self.secret)
        self.assertIs(caught.exception,error)
        self.client.post.assert_called_once()
