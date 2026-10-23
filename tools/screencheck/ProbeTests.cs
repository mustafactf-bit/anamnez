using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public class ProbeTests {
    static string helper, result;
    static int exit=1;
    static void Require(bool ok,string label) { if(!ok)throw new Exception(label); }
    static string Run(string args) {
        var process=Process.Start(new ProcessStartInfo { FileName=helper,Arguments=args,UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,RedirectStandardOutput=true });
        if(!process.WaitForExit(15000)) { process.Kill();throw new Exception("probe_timeout"); }
        Require(process.ExitCode==0,"probe_exit_code");
        return process.StandardOutput.ReadToEnd();
    }
    [STAThread] public static int Main(string[] args) {
        helper=args[0];result=args[1];
        try {
            Require(Run("--self-test").Contains("PASS"),"self_test");
            var form=new Form { Text="SENTETIK_KISI_7281 — TC 12345678901", Width=500,Height=250,Opacity=0,ShowInTaskbar=false };
            var label=new Label { Text="Anamnez",Top=10,Left=10,AutoSize=true };
            var text=new TextBox { Text="SENTETIK_KISI_7281 12345678901 0555 123 45 67 Hastalik notu",Multiline=true,Top=40,Left=10,Width=440,Height=90 };
            form.Controls.Add(label);form.Controls.Add(text);
            string original=text.Text;
            form.Shown+=(s,e)=> {
                IntPtr handle=form.Handle;
                ThreadPool.QueueUserWorkItem(_=> {
                    string path=Path.Combine(Path.GetTempPath(),"screencheck-test-"+Guid.NewGuid().ToString("N")+".json");
                    try {
                        Run("--probe "+handle.ToInt64()+" "+Process.GetCurrentProcess().Id+" \""+path+"\"");
                        string json=File.ReadAllText(path,Encoding.UTF8);
                        Require(!json.Contains("SENTETIK_KISI") && !json.Contains("12345678901") && !json.Contains("0555"),"privacy");
                        var data=new JavaScriptSerializer().DeserializeObject(json) as Dictionary<string,object>;
                        Require(data!=null && data.ContainsKey("nodes"),"report_schema");
                        var nodes=data["nodes"] as object[];
                        Require(nodes!=null && nodes.Length>=3,"structure_detected");
                        bool foundAnamnesis=false,foundEditable=false;
                        var allowed=new HashSet<string>(new[] {"index","parent","depth","control_type","label_hint","enabled","offscreen","value_pattern","text_pattern","read_only"});
                        foreach(var raw in nodes) {
                            var node=(Dictionary<string,object>)raw;
                            foreach(var key in node.Keys)Require(allowed.Contains(key),"metadata_keys_only");
                            if((string)node["label_hint"]=="anamnesis")foundAnamnesis=true;
                            if(((string)node["control_type"]=="ControlType.Edit" || (string)node["control_type"]=="ControlType.Document") && ((bool)node["value_pattern"] || (bool)node["text_pattern"]))foundEditable=true;
                        }
                        Require(foundAnamnesis,"fixed_label_detected");Require(foundEditable,"text_or_value_pattern_detected");
                        Run("--probe 0 0 \""+path+"\"");
                        var invalid=new JavaScriptSerializer().DeserializeObject(File.ReadAllText(path)) as Dictionary<string,object>;
                        Require((string)invalid["status"]=="target_changed","missing_target");
                        form.BeginInvoke((Action)(()=> {
                            try {
                                Require(text.Text==original,"target_unmodified");
                                Require(form.Text=="SENTETIK_KISI_7281 — TC 12345678901","title_unmodified");
                                File.WriteAllText(result,"PASS: fixed-label privacy, metadata schema, UIA structure, text/value pattern, missing target, unchanged source text/title.");exit=0;
                            } catch(Exception error) { File.WriteAllText(result,"FAIL: "+error.Message); }
                            form.Close();
                        }));
                    } catch(Exception error) {
                        form.BeginInvoke((Action)(()=> { File.WriteAllText(result,"FAIL: "+error.Message);form.Close(); }));
                    } finally { try { if(File.Exists(path))File.Delete(path); } catch(Exception) {} }
                });
            };
            Application.Run(form);return exit;
        } catch(Exception error) { File.WriteAllText(result,"FAIL: "+error.Message);return 1; }
    }
}
