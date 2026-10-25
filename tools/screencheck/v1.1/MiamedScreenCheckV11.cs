// Miamed ScreenCheck v1.1 - read-only UI Automation metadata inspector.
// Never exports field values, raw accessible names/IDs, window titles, patient identifiers or screenshots.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Mail;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Automation;
using System.Windows.Forms;
using System.Drawing;

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
    [DataMember] public bool focusable;
    [DataMember] public bool? read_only;
}
[DataContract] public class Report {
    [DataMember] public string tool_version="1.1.0";
    [DataMember] public string status="metadata_only";
    [DataMember] public string timestamp=DateTimeOffset.Now.ToString("o");
    [DataMember] public string privacy="Metadata only: no values, patient data, raw names, window titles, AutomationIds or images.";
    [DataMember] public string selected_section="anamnesis";
    [DataMember] public string scan_scope="full_window"; // Section is an operator label; it is not a restricted subtree.
    [DataMember] public bool truncated;
    [DataMember] public string truncated_reason="none";
    [DataMember] public int skipped;
    [DataMember] public int elapsed_ms;
    [DataMember] public List<NodeInfo> nodes=new List<NodeInfo>();
}
public static class Sections {
    public static string Parse(string x) {
        switch(x) {
            case "complaint": case "medical_history": case "family_history": case "anamnesis": return x;
            default: return "anamnesis";
        }
    }
}
public static class Probe {
    public static string Hint(string name) {
        if(name==null || name.Length>80) return "other";
        switch(name.Trim().TrimEnd(':').ToLowerInvariant()) {
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
    public static bool Available(AutomationElement x, AutomationProperty property) {
        var y=x.GetCurrentPropertyValue(property,true);
        return y is bool && (bool)y;
    }
    public static bool? ReadOnly(AutomationElement x) {
        var y=x.GetCurrentPropertyValue(ValuePattern.IsReadOnlyProperty,true);
        return y is bool ? (bool?)y : null;
    }
    public static string ToJson(Report data) {
        using(var s=new MemoryStream()) {
            new DataContractJsonSerializer(typeof(Report)).WriteObject(s,data);
            return Encoding.UTF8.GetString(s.ToArray());
        }
    }
    public static Report Scan(IntPtr hwnd,int pid,string selectedSection) {
        var report=new Report { selected_section=Sections.Parse(selectedSection) };
        uint actual; Native.GetWindowThreadProcessId(hwnd,out actual);
        if(actual!=(uint)pid || !Native.IsWindowVisible(hwnd)) { report.status="target_changed";return report; }
        var root=AutomationElement.FromHandle(hwnd);
        if(root.Current.ProcessId!=pid) { report.status="target_changed";return report; }
        var pending=new Stack<Tuple<AutomationElement,int,int>>();
        pending.Push(Tuple.Create(root,-1,0));
        var watch=Stopwatch.StartNew();
        var reasons=new SortedSet<string>();
        while(pending.Count>0) {
            if(report.nodes.Count>=3500) { reasons.Add("node_limit");break; }
            if(watch.ElapsedMilliseconds>20000) { reasons.Add("time_limit");break; }
            var tuple=pending.Pop();var node=tuple.Item1;
            try {
                var current=node.Current;
                if(current.ProcessId!=pid) { report.skipped++;continue; }
                int index=report.nodes.Count;
                bool skipName=current.ControlType==ControlType.Edit || current.ControlType==ControlType.Document || current.IsPassword;
                report.nodes.Add(new NodeInfo {
                    index=index,parent=tuple.Item2,depth=tuple.Item3,
                    control_type=current.ControlType.ProgrammaticName,
                    label_hint=skipName ? "not_read" : Hint(current.Name),
                    enabled=current.IsEnabled,offscreen=current.IsOffscreen,
                    focusable=Available(node,AutomationElement.IsKeyboardFocusableProperty),
                    value_pattern=Available(node,AutomationElement.IsValuePatternAvailableProperty),
                    text_pattern=Available(node,AutomationElement.IsTextPatternAvailableProperty),
                    read_only=ReadOnly(node)
                });
                if(tuple.Item3>=28) { // Keep scanning siblings, but report this branch as incomplete.
                    var child=TreeWalker.ControlViewWalker.GetFirstChild(node);
                    if(child!=null) reasons.Add("depth_limit");
                    continue;
                }
                var children=new List<AutomationElement>();
                var candidate=TreeWalker.ControlViewWalker.GetFirstChild(node);
                while(candidate!=null && children.Count<1000 && watch.ElapsedMilliseconds<=20000) {
                    children.Add(candidate);
                    candidate=TreeWalker.ControlViewWalker.GetNextSibling(candidate);
                }
                if(candidate!=null) reasons.Add(children.Count>=1000?"children_limit":"time_limit");
                for(int k=children.Count-1;k>=0;k--)pending.Push(Tuple.Create(children[k],index,tuple.Item3+1));
            } catch(Exception) { report.skipped++; }
        }
        report.elapsed_ms=(int)Math.Min(watch.ElapsedMilliseconds,int.MaxValue);
        Native.GetWindowThreadProcessId(hwnd,out actual);
        if(actual!=(uint)pid) { report.nodes.Clear();report.status="target_changed"; }
        else if(reasons.Count>0 || report.skipped>0)report.status="partial_metadata_only";
        report.truncated=reasons.Count>0;
        report.truncated_reason=reasons.Count>0?String.Join(",",new List<string>(reasons).ToArray()):"none";
        return report;
    }
}
public static class Native {
    public delegate bool WindowCallback(IntPtr hwnd,IntPtr param);
    [DllImport("user32.dll")] public static extern bool EnumWindows(WindowCallback callback,IntPtr param);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint process);
}
public class Choice {
    public IntPtr hwnd;public int pid;public string label;
    public override string ToString() { return label; }
}
public static class MailConfig {
    // DPAPI encryption is bound to the Windows account. Never include credentials in the JSON report.
    static string PathName { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"AnamnezAsistani","ScreenCheck-v1.1","mail.dat"); } }
    public static void Disable() {
        if(File.Exists(PathName)) File.Delete(PathName);
    }
    public static string[] Read() {
        if(!File.Exists(PathName)) return null;
        try {
            byte[] encrypted=File.ReadAllBytes(PathName);
            string raw=Encoding.UTF8.GetString(ProtectedData.Unprotect(encrypted,null,DataProtectionScope.CurrentUser));
            string[] lines=raw.Split(new[]{'\n'},2);
            if(lines.Length!=2)return null;
            return lines;
        } catch(Exception) { return null; }
    }
    public static void Store(string email,string appPassword) {
        email=email.Trim();appPassword=appPassword.Replace(" ","").Trim();
        var parsed=new MailAddress(email);
        if(parsed.Address!=email || (!email.EndsWith("@gmail.com",StringComparison.OrdinalIgnoreCase) && !email.EndsWith("@googlemail.com",StringComparison.OrdinalIgnoreCase)))
            throw new ArgumentException("Gmail adresinizi girin.");
        if(appPassword.Length!=16)throw new ArgumentException("Normal Gmail şifreniz değil, 16 karakterli uygulama şifrenizi girin.");
        string folder=Path.GetDirectoryName(PathName);
        Directory.CreateDirectory(folder);
        byte[] protectedBytes=ProtectedData.Protect(Encoding.UTF8.GetBytes(email+"\n"+appPassword),null,DataProtectionScope.CurrentUser);
        string temp=PathName+".tmp";
        File.WriteAllBytes(temp,protectedBytes);
        if(File.Exists(PathName))File.Delete(PathName);
        File.Move(temp,PathName);
    }
    public static void SendReport(string path) {
        var config=Read();
        if(config==null)throw new InvalidOperationException("E-posta ayarı eksik.");
        using(var message=new MailMessage(config[0],config[0])) {
            message.Subject="Anamnez Asistanı — Miamed teknik ekran raporu v1.1";
            message.Body="Bu ek yalnızca Windows arayüzünün teknik metadata raporudur. Hasta içeriği, kimlik bilgisi veya ekran görüntüsü içermez. Raporu yalnızca kurum izni kapsamında kullanın.";
            message.Attachments.Add(new Attachment(path,"application/json"));
            using(var smtp=new SmtpClient("smtp.gmail.com",587)) {
                smtp.EnableSsl=true;
                smtp.Timeout=20000;
                smtp.UseDefaultCredentials=false;
                smtp.Credentials=new NetworkCredential(config[0],config[1]);
                smtp.Send(message);
            }
        }
    }
}
public class SetupWindow : Form {
    readonly TextBox address=new TextBox(),secret=new TextBox();
    readonly CheckBox permit=new CheckBox();
    public bool saved=false;
    public SetupWindow() {
        Text="Bir kez e-posta kurulumu";Size=new Size(560,370);FormBorderStyle=FormBorderStyle.FixedDialog;
        MaximizeBox=false;StartPosition=FormStartPosition.CenterParent;
        var layout=new TableLayoutPanel { Dock=DockStyle.Fill,Padding=new Padding(18),ColumnCount=1,RowCount=7 };
        Controls.Add(layout);
        layout.Controls.Add(new Label { Text="1. Gmail adresinizi girin. Rapor aynı adrese gönderilecek.",AutoSize=true });
        address.Dock=DockStyle.Top;layout.Controls.Add(address);
        layout.Controls.Add(new Label { Text="2. Gmail uygulama şifresi (normal hesap şifrenizi GİRMEYİN):",AutoSize=true });
        secret.UseSystemPasswordChar=true;secret.Dock=DockStyle.Top;layout.Controls.Add(secret);
        var link=new LinkLabel { Text="Uygulama şifresi oluşturma sayfası (Google)",AutoSize=true };
        link.LinkClicked+=(s,e)=> { try { Process.Start("https://myaccount.google.com/apppasswords"); }catch(Exception){} };
        layout.Controls.Add(link);
        permit.Text="Kurumun teknik metadata raporunun kişisel Gmail hesabıma gönderilmesine izin verdiğini doğruluyorum.";
        permit.AutoSize=true;permit.MaximumSize=new Size(490,60);layout.Controls.Add(permit);
        var button=new Button { Text="Kaydet ve otomatik göndermeyi aç",AutoSize=true,Height=38,Dock=DockStyle.Top };
        layout.Controls.Add(button);
        var old=MailConfig.Read();if(old!=null)address.Text=old[0];
        button.Click+=(s,e)=> {
            if(!permit.Checked) { MessageBox.Show("E-posta gönderimi için kurum iznini doğrulamanız gerekir. İzin yoksa sadece yerel rapor kullanın.");return; }
            try {
                string p=secret.Text;
                if(String.IsNullOrWhiteSpace(p) && old!=null && address.Text.Trim()==old[0])p=old[1];
                MailConfig.Store(address.Text,p);
                saved=true;DialogResult=DialogResult.OK;Close();
            } catch(Exception ex) { MessageBox.Show(ex is ArgumentException ? ex.Message : "Ayarlar kaydedilemedi. Windows hesabı ve yazma iznini kontrol edin."); }
        };
    }
}
public class MainWindow : Form {
    readonly ComboBox programs=new ComboBox(),sections=new ComboBox();
    readonly Button refresh=new Button(),start=new Button(),setup=new Button(),folder=new Button(),retry=new Button(),disableMail=new Button();
    readonly Label status=new Label();
    Process worker;
    string lastReport;
    public MainWindow() {
        Text="Miamed Ekran Kontrolü v1.1 — salt okunur";Width=820;Height=480;
        MinimumSize=new Size(730,440);StartPosition=FormStartPosition.CenterScreen;
        var root=new TableLayoutPanel { Dock=DockStyle.Fill,Padding=new Padding(18),ColumnCount=1,RowCount=10 };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));Controls.Add(root);
        root.Controls.Add(new Label { Text="MİAMED EKRAN KONTROLÜ  |  v1.1",Font=new Font(Font.FontFamily,16,FontStyle.Bold),AutoSize=true });
        root.Controls.Add(new Label { Text="Bu araç sadece düğme, sekme ve giriş alanlarının teknik özelliklerini inceler. Hastaya veya Miamed kaydına hiçbir şey yazmaz.",AutoSize=true,MaximumSize=new Size(740,44) });
        root.Controls.Add(new Label { Text="1. Miamed'i açın. Listede otomatik seçilmiyorsa programı seçin:",AutoSize=true });
        programs.DropDownStyle=ComboBoxStyle.DropDownList;programs.Dock=DockStyle.Fill;root.Controls.Add(programs);
        root.Controls.Add(new Label { Text="2. Miamed'de ilgili sekmeyi ELLE açın, sonra bu taramaya bölüm etiketi verin (tarama tüm pencereyi inceler):",AutoSize=true });
        sections.DropDownStyle=ComboBoxStyle.DropDownList;sections.Dock=DockStyle.Fill;
        sections.Items.AddRange(new object[]{"Anamnez","Şikâyet","Özgeçmiş","Soygeçmiş"});sections.SelectedIndex=0;root.Controls.Add(sections);
        var actions=new FlowLayoutPanel { AutoSize=true,Dock=DockStyle.Fill,WrapContents=true };
        start.Text="3. Rapor al ve otomatik e-postala";start.AutoSize=true;start.Height=42;
        refresh.Text="Listeyi yenile";refresh.AutoSize=true;refresh.Height=42;
        setup.Text="E-posta ayarları";setup.AutoSize=true;setup.Height=42;
        folder.Text="Rapor klasörünü aç";folder.AutoSize=true;folder.Height=42;
        retry.Text="Son raporu tekrar gönder";retry.AutoSize=true;retry.Height=42;retry.Enabled=false;
        disableMail.Text="E-postayı kapat";disableMail.AutoSize=true;disableMail.Height=42;
        actions.Controls.Add(start);actions.Controls.Add(refresh);actions.Controls.Add(setup);actions.Controls.Add(disableMail);actions.Controls.Add(retry);actions.Controls.Add(folder);root.Controls.Add(actions);
        status.Text="Hazır. E-posta için ilk seferde 'E-posta ayarları' bölümünü kurun.";
        status.AutoSize=true;status.MaximumSize=new Size(750,100);root.Controls.Add(status);
        root.Controls.Add(new Label { Text="Kurum izni olmadan raporu kişisel e-postaya göndermeyin. E-posta kurulmazsa rapor yalnızca bu bilgisayara kaydedilir. Kısmi tarama başarısızlık değildir.",AutoSize=true,MaximumSize=new Size(740,60),ForeColor=Color.DarkRed });
        refresh.Click+=(s,e)=>ListPrograms();setup.Click+=(s,e)=>ConfigureMail();disableMail.Click+=(s,e)=>DisableMail();folder.Click+=(s,e)=>OpenFolder();start.Click+=(s,e)=>RunScan();retry.Click+=(s,e)=>RetrySend();
        FormClosing+=(s,e)=> { try { if(worker!=null && !worker.HasExited)worker.Kill(); }catch(Exception){} };
        ListPrograms();
        if(MailConfig.Read()==null)status.Text="İlk kullanım: 'E-posta ayarları' → Gmail + uygulama şifresi → kurum izni. Sonra bir tuşla rapor.";
    }
    static string ReportsFolder {get {return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"Miamed-Teknik-Raporlar");}}
    void OpenFolder() { try {Directory.CreateDirectory(ReportsFolder);Process.Start("explorer.exe",ReportsFolder);}catch(Exception){MessageBox.Show("Klasör açılamadı. Belgeler klasörünüzü kontrol edin.");} }
    void ConfigureMail() { using(var dialog=new SetupWindow())dialog.ShowDialog(this);status.Text=MailConfig.Read()==null?"E-posta ayarı yok; rapor yalnızca kaydedilecek.":"E-posta hazır. Taramadan sonra otomatik gönderilecek."; }
    void DisableMail() {
        if(MessageBox.Show("Bu Windows hesabındaki Gmail uygulama şifresi kaydı silinsin ve otomatik e-posta kapatılsın mı? Rapor dosyaları korunur.", "E-posta ayarlarını sil", MessageBoxButtons.YesNo, MessageBoxIcon.Question)!=DialogResult.Yes)return;
        try { MailConfig.Disable();retry.Enabled=false;status.Text="Otomatik e-posta kapatıldı. Raporlar yalnızca bilgisayara kaydedilir."; }
        catch(Exception) { MessageBox.Show("E-posta ayarı kaldırılamadı; dosya izinlerini kontrol edin."); }
    }
    void ListPrograms() {
        programs.Items.Clear();int self=Process.GetCurrentProcess().Id;
        Native.EnumWindows((hwnd,arg)=> {
            if(!Native.IsWindowVisible(hwnd))return true;
            uint pid;Native.GetWindowThreadProcessId(hwnd,out pid);
            if(pid==0 || pid==self)return true;
            try {
                var process=Process.GetProcessById((int)pid);
                // Do not read window titles, command lines or any patient context.
                programs.Items.Add(new Choice {hwnd=hwnd,pid=(int)pid,label=process.ProcessName+" (PID "+pid+")"});
            }catch(Exception){}
            return true;
        },IntPtr.Zero);
        for(int i=0;i<programs.Items.Count;i++)if(programs.Items[i].ToString().IndexOf("miamed",StringComparison.OrdinalIgnoreCase)>=0){programs.SelectedIndex=i;break;}
        if(programs.SelectedIndex<0 && programs.Items.Count>0)status.Text="Miamed otomatik seçilemedi. Program adını bilmiyorsanız bilgi işleme sorun.";
    }
    void RetrySend() {
        if(lastReport==null || !File.Exists(lastReport) || MailConfig.Read()==null)return;
        retry.Enabled=false;start.Enabled=false;status.Text="Son rapor e-postayla gönderiliyor...";
        ThreadPool.QueueUserWorkItem(_=> {
            string result;
            try { MailConfig.SendReport(lastReport);result="Son rapor Gmail adresinize gönderildi."; }
            catch(Exception) { result="Gönderim başarısız. Rapor dosyası Belgeler klasöründe duruyor; e-posta ayarlarını kontrol edin."; }
            if(IsDisposed || !IsHandleCreated)return;
            try {BeginInvoke((Action)(()=> {retry.Enabled=true;start.Enabled=true;status.Text=result;}));}catch(Exception){}
        });
    }
    void RunScan() {
        var chosen=programs.SelectedItem as Choice;
        if(chosen==null){MessageBox.Show("Önce Miamed programını seçin.");return;}
        if(chosen.label.IndexOf("miamed",StringComparison.OrdinalIgnoreCase)<0 &&
           MessageBox.Show("Bu programın adı Miamed olarak görünmüyor. Hastane bilgi işleminden doğru uygulamayı doğruladınız mı? Yanlış uygulamanın teknik metaverisini taramayın.","Program doğrulaması",MessageBoxButtons.YesNo,MessageBoxIcon.Warning)!=DialogResult.Yes)return;
        string section=new[]{"anamnesis","complaint","medical_history","family_history"}[sections.SelectedIndex];
        start.Enabled=false;retry.Enabled=false;setup.Enabled=false;disableMail.Enabled=false;refresh.Enabled=false;programs.Enabled=false;sections.Enabled=false;
        status.Text="Tarama yapılıyor. Lütfen Miamed penceresini kapatmayın...";
        string temp=Path.Combine(Path.GetTempPath(),"miamed-v11-"+Guid.NewGuid().ToString("N")+".json");
        ThreadPool.QueueUserWorkItem(_=> {
            string result;
            try {
                var info=new ProcessStartInfo { FileName=System.Reflection.Assembly.GetExecutingAssembly().Location,
                    Arguments="--probe "+chosen.hwnd.ToInt64()+" "+chosen.pid+" \""+temp+"\" "+section,
                    UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden };
                worker=Process.Start(info);
                if(!worker.WaitForExit(35000)){worker.Kill();worker.WaitForExit(2000);result="Tarama süresi doldu; Miamed değişmedi. Yeniden deneyin.";}
                else if(worker.ExitCode!=0 || !File.Exists(temp))result="Teknik tarama tamamlanamadı. Bilgi işlemden yardım isteyin.";
                else {
                    string json=File.ReadAllText(temp,Encoding.UTF8);
                    var report=new DataContractJsonSerializer(typeof(Report));
                    Report parsed;using(var stream=new MemoryStream(Encoding.UTF8.GetBytes(json)))parsed=(Report)report.ReadObject(stream);
                    if(parsed.status=="target_changed" || parsed.nodes.Count==0)result="Miamed penceresi değişti ya da kapandı. Tekrar seçin.";
                    else {
                        Directory.CreateDirectory(ReportsFolder);
                        string savedPath=Path.Combine(ReportsFolder,"Miamed-v1.1-"+section+"-"+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+".json");
                        File.WriteAllText(savedPath,json,new UTF8Encoding(false));
                        lastReport=savedPath;
                        var cfg=MailConfig.Read();
                        if(cfg==null)result="Rapor bilgisayara kaydedildi ("+parsed.nodes.Count+" öğe). Otomatik e-posta için Ayarlar'ı tamamlayın.";
                        else {
                            try {MailConfig.SendReport(lastReport);result="E-POSTA GÖNDERİLDİ: "+cfg[0]+". Rapor ayrıca Belgeler klasöründe ("+parsed.nodes.Count+" öğe).";}
                            catch(Exception) {result="RAPOR KAYDEDİLDİ, E-POSTA GÖNDERİLEMEDİ. Gmail uygulama şifresi ve ağ erişimini kontrol edip tekrar tarayın.";}
                        }
                        if(parsed.truncated)result+=" Not: tarama kısmi ("+parsed.truncated_reason+").";
                    }
                }
            } catch(Exception) {result="İşlem tamamlanamadı. Miamed verisi değiştirilmedi.";}
            finally {try {if(File.Exists(temp))File.Delete(temp);}catch(Exception){} }
            if(IsDisposed || !IsHandleCreated)return;
            try {BeginInvoke((Action)(()=>{start.Enabled=true;retry.Enabled=lastReport!=null && MailConfig.Read()!=null;setup.Enabled=true;disableMail.Enabled=true;refresh.Enabled=true;programs.Enabled=true;sections.Enabled=true;status.Text=result;}));}catch(Exception){}
        });
    }
}
public static class Program {
    [STAThread] public static int Main(string[] args) {
        if(args.Length==1 && args[0]=="--self-test") {
            bool safe=Probe.Hint("Ahmet Örnek 12345678901")=="other" && Probe.Hint("Anamnez")=="anamnesis";
            string json=Probe.ToJson(new Report {nodes=new List<NodeInfo>{new NodeInfo{control_type="ControlType.Edit",label_hint="not_read"}}});
            safe=safe && !json.Contains("Ahmet") && !json.Contains("12345678901") && json.Contains("1.1.0");
            Console.WriteLine(safe?"PASS: privacy and schema":"FAIL");return safe?0:1;
        }
        if((args.Length==4 || args.Length==5) && args[0]=="--probe") {
            try {
                int pid=int.Parse(args[2]);IntPtr hwnd=new IntPtr(long.Parse(args[1]));
                var data=Probe.Scan(hwnd,pid,args.Length==5?args[4]:"anamnesis");
                File.WriteAllText(args[3],Probe.ToJson(data),new UTF8Encoding(false));return 0;
            } catch(Exception) {return 2;}
        }
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainWindow());return 0;
    }
}
