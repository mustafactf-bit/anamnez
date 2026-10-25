// No patient information, internet or Miamed needed: synthetic Windows UIA tests.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public static class ProbeTestsV11 {
    static string helper;
    static string output;
    static int code=1;
    static void Check(bool success,string what) { if(!success) throw new InvalidOperationException(what); }
    static Dictionary<string,object> RunProbe(IntPtr hwnd,int pid,string section) {
        var path=Path.Combine(Path.GetTempPath(),"miamed-v11-synth-"+Guid.NewGuid().ToString("N")+".json");
        try {
            string args="--probe "+hwnd.ToInt64()+" "+pid+" \""+path+"\" "+section;
            using(var process=Process.Start(new ProcessStartInfo { FileName=helper,Arguments=args,UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden })) {
                Check(process.WaitForExit(30000),"probe_timeout");
                Check(process.ExitCode==0,"probe_exit_code");
            }
            string json=File.ReadAllText(path,Encoding.UTF8);
            foreach(string unsafeValue in new[]{"SENTETIK_KISI_7281","12345678901","0555 123","SYNTHETIC_WINDOW_PRIVATE"})
                Check(!json.Contains(unsafeValue),"privacy_exported_"+unsafeValue);
            return new JavaScriptSerializer().DeserializeObject(json) as Dictionary<string,object>;
        } finally { try {File.Delete(path);}catch(Exception){} }
    }
    [STAThread] public static int Main(string[] args) {
        if(args.Length!=2) return 3;
        helper=args[0];output=args[1];
        try {
            using(var self=Process.Start(new ProcessStartInfo {FileName=helper,Arguments="--self-test",UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden})) {
                Check(self.WaitForExit(15000)&&self.ExitCode==0,"self_test");
            }
            var missing=RunProbe(IntPtr.Zero,0,"anamnesis");
            Check((string)missing["status"]=="target_changed","missing_target_status");
            Check(((object[])missing["nodes"]).Length==0,"missing_target_nodes");
            var form=new Form {Text="SYNTHETIC_WINDOW_PRIVATE",Width=510,Height=320,Opacity=0,ShowInTaskbar=false};
            var name=new Label {Text="Anamnez",Left=8,Top=8,AutoSize=true};
            var input=new TextBox {Text="SENTETIK_KISI_7281 12345678901 0555 123 45 67",Multiline=true,Left=8,Top=40,Width=465,Height=125};
            var tabs=new TabControl {Left=8,Top=177,Width=465,Height=75};
            tabs.TabPages.Add(new TabPage("Şikâyet"));
            tabs.TabPages.Add(new TabPage("Özgeçmiş"));
            form.Controls.Add(name);form.Controls.Add(input);form.Controls.Add(tabs);
            string original=input.Text;
            form.Shown+=(s,e)=>{
                IntPtr handle=form.Handle;
                ThreadPool.QueueUserWorkItem(_=> {
                try {
                    var doc=RunProbe(handle,Process.GetCurrentProcess().Id,"complaint");
                    Check((string)doc["tool_version"]=="1.1.0","tool_version");
                    Check((string)doc["selected_section"]=="complaint","selected_section");
                    Check((string)doc["scan_scope"]=="full_window","scan_scope");
                    Check((string)doc["status"]=="metadata_only","scan_status");
                    Check((string)doc["truncated_reason"]=="none","truncation_reason");
                    var nodes=(object[])doc["nodes"];
                    Check(nodes.Length>=4,"control_tree");
                    var allowed=new HashSet<string>(new[]{"index","parent","depth","control_type","label_hint","enabled","offscreen","value_pattern","text_pattern","focusable","read_only"});
                    bool foundLabel=false,foundEdit=false;
                    foreach(var entry in nodes) {
                        var node=(Dictionary<string,object>)entry;
                        foreach(string key in node.Keys)Check(allowed.Contains(key),"unexpected_exported_field_"+key);
                        if((string)node["label_hint"]=="anamnesis") foundLabel=true;
                        if(((string)node["control_type"]=="ControlType.Edit" || (string)node["control_type"]=="ControlType.Document") && ((bool)node["value_pattern"]||(bool)node["text_pattern"])) foundEdit=true;
                    }
                    Check(foundLabel,"anamnesis_label");Check(foundEdit,"editable_metadata");
                    form.BeginInvoke((Action)(()=> {
                        try {
                            Check(input.Text==original,"source_modified");
                            Check(form.Text=="SYNTHETIC_WINDOW_PRIVATE","title_modified");
                            File.WriteAllText(output,"PASS v1.1: self-test, missing target, private labels/values excluded, structure, editable metadata, section label, unchanged source and truncation.");
                            code=0;
                        } catch(Exception ex){File.WriteAllText(output,"FAIL "+ex.Message);} finally {form.Close();}
                    }));
                } catch(Exception ex){form.BeginInvoke((Action)(()=>{File.WriteAllText(output,"FAIL "+ex.Message);form.Close();}));}
                });
            };
            Application.Run(form);return code;
        } catch(Exception ex) {File.WriteAllText(output,"FAIL "+ex.Message);return 1;}
    }
}
