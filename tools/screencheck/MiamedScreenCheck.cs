// Read-only UI Automation diagnostics. No input injection, clipboard, credentials,
// screenshots, field values, window titles, raw names or AutomationIds are exported.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Threading;
using System.Windows.Automation;
using System.Windows.Forms;

[DataContract] public class NodeInfo {
    [DataMember] public int index;
    [DataMember] public int parent;
    [DataMember] public int depth;
    [DataMember] public string control_type;
    [DataMember] public string label_hint;
    [DataMember] public bool enabled;
    [DataMember] public bool offscreen;
    [DataMember] public bool value_pattern;
    [DataMember] public bool text_pattern;
    [DataMember] public bool? read_only;
}
[DataContract] public class Report {
    [DataMember] public string tool_version = "1.0.0";
    [DataMember] public string status = "metadata_only";
    [DataMember] public string timestamp = DateTimeOffset.Now.ToString("o");
    [DataMember] public string privacy = "No field values, raw names, window titles, IDs, screenshots or patient identifiers exported.";
    [DataMember] public bool truncated;
    [DataMember] public int skipped;
    [DataMember] public List<NodeInfo> nodes = new List<NodeInfo>();
}

public static class Inspector {
    // Comparisons produce only the fixed English classifications below.
    public static string Hint(string name) {
        if (name == null || name.Length > 80) return "other";
        switch (name.Trim().TrimEnd(':').ToLowerInvariant()) {
            case "anamnez": case "anamnez bilgileri": case "anamnez giriş": return "anamnesis";
            case "şikayet": case "şikâyet": case "şikayeti": return "complaint";
            case "özgeçmiş": return "medical_history";
            case "soygeçmiş": return "family_history";
            case "hasta": case "hasta bilgileri": return "patient_label";
            case "protokol": case "protokol no": case "başvuru": case "başvuru no": return "encounter_label";
            case "kaydet": return "save_label";
            default: return "other";
        }
    }
    public static string Serialize(Report value) {
        using (var buffer = new MemoryStream()) {
            new DataContractJsonSerializer(typeof(Report)).WriteObject(buffer, value);
            return Encoding.UTF8.GetString(buffer.ToArray());
        }
    }
    public static bool Boolean(AutomationElement node, AutomationProperty property) {
        var value = node.GetCurrentPropertyValue(property, true);
        return value is bool && (bool)value;
    }
    public static bool? ReadOnly(AutomationElement node) {
        var value=node.GetCurrentPropertyValue(ValuePattern.IsReadOnlyProperty,true);
        return value is bool ? (bool?)value : null;
    }
    public static Report Scan(IntPtr handle, int expectedPid) {
        var report = new Report();
        uint pid; Native.GetWindowThreadProcessId(handle, out pid);
        if (pid != expectedPid || !Native.IsWindowVisible(handle)) { report.status="target_changed"; return report; }
        var root = AutomationElement.FromHandle(handle);
        if (root.Current.ProcessId != expectedPid) { report.status="target_changed"; return report; }
        var pending = new Stack<Tuple<AutomationElement,int,int>>();
        pending.Push(Tuple.Create(root, -1, 0));
        var watch = Stopwatch.StartNew();
        while (pending.Count > 0) {
            if (report.nodes.Count >= 1500 || watch.ElapsedMilliseconds > 10000) { report.truncated=true; break; }
            var item=pending.Pop(); var node=item.Item1;
            try {
                var current=node.Current;
                if (current.ProcessId != expectedPid) { report.skipped++; continue; }
                var type=current.ControlType;
                int index=report.nodes.Count;
                // Edit/Document names can themselves contain their field value.
                bool skipName=type==ControlType.Edit || type==ControlType.Document || current.IsPassword;
                report.nodes.Add(new NodeInfo {
                    index=index, parent=item.Item2, depth=item.Item3,
                    control_type=type.ProgrammaticName,
                    label_hint=skipName ? "not_read" : Hint(current.Name),
                    enabled=current.IsEnabled, offscreen=current.IsOffscreen,
                    value_pattern=Boolean(node,AutomationElement.IsValuePatternAvailableProperty),
                    text_pattern=Boolean(node,AutomationElement.IsTextPatternAvailableProperty),
                    read_only=ReadOnly(node)
                });
                if (item.Item3 >= 16) { report.truncated=true; continue; }
                var children=new List<AutomationElement>();
                var child=TreeWalker.ControlViewWalker.GetFirstChild(node);
                while (child!=null && children.Count < 500 && watch.ElapsedMilliseconds <= 10000) {
                    children.Add(child); child=TreeWalker.ControlViewWalker.GetNextSibling(child);
                }
                if (child!=null) report.truncated=true;
                for (int i=children.Count-1;i>=0;i--) pending.Push(Tuple.Create(children[i],index,item.Item3+1));
            } catch (Exception) { report.skipped++; }
        }
        Native.GetWindowThreadProcessId(handle,out pid);
        if (pid!=expectedPid) { report.nodes.Clear(); report.status="target_changed"; }
        else if (report.truncated || report.skipped>0) report.status="partial_metadata_only";
        return report;
    }
}

public static class Native {
    public delegate bool Callback(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] public static extern bool EnumWindows(Callback callback,IntPtr parameter);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
}

public class Choice {
    public IntPtr Handle; public int Pid; public string Display;
    public override string ToString() { return Display; }
}

public class CheckWindow : Form {
    readonly ComboBox choices=new ComboBox();
    readonly Button inspect=new Button();
    readonly Button save=new Button();
    readonly Label state=new Label();
    string reportJson;
    Process worker;
    public CheckWindow() {
        Text="Miamed Ekran Kontrolü — salt okunur"; Width=760; Height=380;
        MinimumSize=new System.Drawing.Size(720,370);
        var layout=new TableLayoutPanel { Dock=DockStyle.Fill, Padding=new Padding(16), ColumnCount=1, RowCount=6 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
        Controls.Add(layout);
        layout.Controls.Add(new Label { Text="Miamed'i açın ve kurumun uygun test ekranını gösterin.\nBu araç hiçbir alana yazmaz, hasta kaydetmez; alan içeriklerini raporlamaz.", AutoSize=true, MaximumSize=new System.Drawing.Size(680,70) });
        layout.Controls.Add(new Label { Text="Miamed'e ait programı seçin (hasta içerebilecek pencere başlıkları gösterilmez):",AutoSize=true });
        choices.Dock=DockStyle.Fill; choices.DropDownStyle=ComboBoxStyle.DropDownList; layout.Controls.Add(choices);
        var actions=new FlowLayoutPanel { AutoSize=true, Dock=DockStyle.Fill };
        var refresh=new Button { Text="Listeyi yenile", AutoSize=true };
        inspect.Text="Yapıyı kontrol et";inspect.AutoSize=true;
        save.Text="Raporu kaydet";save.AutoSize=true;save.Enabled=false;
        actions.Controls.Add(refresh);actions.Controls.Add(inspect);actions.Controls.Add(save);layout.Controls.Add(actions);
        state.AutoSize=true; state.MaximumSize=new System.Drawing.Size(680,110);layout.Controls.Add(state);
        layout.Controls.Add(new Label { Text="Bu rapor yalnızca teknik ön incelemedir. Anamnez aktarımının veya doğru hasta eşleştirmesinin çalıştığını kanıtlamaz.",AutoSize=true,MaximumSize=new System.Drawing.Size(680,60) });
        refresh.Click+=(s,e)=>RefreshList(); inspect.Click+=(s,e)=>StartScan(); save.Click+=(s,e)=>SaveReport();
        FormClosing+=(s,e)=> { try { if(worker!=null && !worker.HasExited) worker.Kill(); } catch(Exception) {} };
        RefreshList();
    }
    void RefreshList() {
        if (!inspect.Enabled) return;
        choices.Items.Clear();int own=Process.GetCurrentProcess().Id;
        Native.EnumWindows((window,parameter)=> {
            if (!Native.IsWindowVisible(window)) return true;
            uint pid;Native.GetWindowThreadProcessId(window,out pid);
            if(pid==own || pid==0)return true;
            try {
                string process=Process.GetProcessById((int)pid).ProcessName;
                choices.Items.Add(new Choice { Handle=window,Pid=(int)pid,Display=process+" (PID "+pid+")" });
            } catch(Exception) {}
            return true;
        },IntPtr.Zero);
        for(int i=0;i<choices.Items.Count;i++) {
            if(choices.Items[i].ToString().ToLowerInvariant().Contains("miamed")) { choices.SelectedIndex=i;break; }
        }
        state.Text="Miamed programını seçin. Belirsizse hastane bilgi işlemine program adını sorabilirsiniz.";
    }
    void StartScan() {
        var selected=choices.SelectedItem as Choice;if(selected==null) { state.Text="Önce Miamed'e ait programı seçin.";return; }
        reportJson=null;save.Enabled=false;inspect.Enabled=false;choices.Enabled=false;
        state.Text="Yalnızca kontrol türleri ve desteklenen alan özellikleri inceleniyor...";
        string path=Path.Combine(Path.GetTempPath(),"MiamedScreenCheck-"+Guid.NewGuid().ToString("N")+".json");
        ThreadPool.QueueUserWorkItem(_=> {
            string json=null;string message;
            try {
                var start=new ProcessStartInfo {
                    FileName=System.Reflection.Assembly.GetExecutingAssembly().Location,
                    Arguments="--probe "+selected.Handle.ToInt64()+" "+selected.Pid+" \""+path+"\"",
                    UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden
                };
                worker=Process.Start(start);
                if(!worker.WaitForExit(20000)) { worker.Kill();worker.WaitForExit(2000);message="Kontrol zaman aşımına uğradı. Miamed'e yazma yapılmadı; bilgi işlemle değerlendirin."; }
                else if(worker.ExitCode!=0 || !File.Exists(path)) message="Ekran yapısına erişilemedi. Yönetici yetkisi istemeden bilgi işlemle değerlendirin.";
                else { json=File.ReadAllText(path,Encoding.UTF8); message="Teknik ön inceleme tamamlandı. Raporu kaydedip paylaşabilirsiniz. Uyumluluk henüz doğrulanmış değildir."; }
            } catch(Exception) { message="Kontrol tamamlanamadı. Hastane bilgi işlemine danışın; kayıtlara yazma yapılmadı."; }
            finally { try { if(File.Exists(path))File.Delete(path); } catch(Exception) {} }
            if(IsDisposed || !IsHandleCreated)return;
            try { BeginInvoke((Action)(()=> { reportJson=json;save.Enabled=json!=null;inspect.Enabled=true;choices.Enabled=true;state.Text=message; })); } catch(Exception) {}
        });
    }
    void SaveReport() {
        if(reportJson==null)return;
        using(var dialog=new SaveFileDialog { Filter="JSON raporu|*.json", FileName="Miamed-Ekran-Kontrol-Raporu.json" }) {
            if(dialog.ShowDialog()!=DialogResult.OK)return;
            try { File.WriteAllText(dialog.FileName,reportJson,new UTF8Encoding(false));state.Text="Kimlik ve alan içeriği içermeyen teknik rapor kaydedildi."; }
            catch(Exception) { state.Text="Rapor kaydedilemedi. Başka bir kayıt konumu seçin."; }
        }
    }
}

public static class Program {
    [STAThread] public static int Main(string[] args) {
        if(args.Length==1 && args[0]=="--self-test") {
            bool ok=Inspector.Hint("Ahmet Örnek 12345678901")=="other" && Inspector.Hint("Anamnez")=="anamnesis" && Inspector.Hint("0555 123 45 67")=="other";
            var report=new Report();report.nodes.Add(new NodeInfo { control_type="ControlType.Edit",label_hint=Inspector.Hint("Ahmet Örnek 12345678901") });
            string json=Inspector.Serialize(report);
            ok=ok && !json.Contains("Ahmet") && !json.Contains("12345678901") && !json.Contains("0555");
            Console.WriteLine(ok ? "PASS: fixed vocabulary and metadata-only serialization" : "FAIL");return ok?0:1;
        }
        if(args.Length==4 && args[0]=="--probe") {
            try {
                var report=Inspector.Scan(new IntPtr(long.Parse(args[1])),int.Parse(args[2]));
                File.WriteAllText(args[3],Inspector.Serialize(report),new UTF8Encoding(false));return 0;
            } catch(Exception) { return 2; }
        }
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new CheckWindow());return 0;
    }
}
