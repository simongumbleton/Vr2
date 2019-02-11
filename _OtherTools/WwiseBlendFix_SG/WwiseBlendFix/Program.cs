using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Xml;
using System.Xml.Linq;

namespace WwiseBlendFix
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                var options = ParseArgs(args);

                var source = options.Source;

                var attr = File.GetAttributes(source);

                string[] workUnitPaths = { source };

                if (attr.HasFlag(FileAttributes.Directory))
                {
                    workUnitPaths = Directory.GetFiles(source, "*.wwu", SearchOption.AllDirectories);
                }

                var groupId = Guid.NewGuid().ToString("B").ToUpper();
                var switchId = Guid.NewGuid().ToString("B").ToUpper();

                switchId = AddDefaultSwitch(options, groupId, out groupId, switchId, out string workUnitId);

                foreach (var path in workUnitPaths)
                {
                    var doc = XDocument.Load(path);

                    bool changed = false;

                    foreach (var blendContainer in doc.Descendants("BlendContainer").ToArray())
                    {
                        var blendList = blendContainer.Elements("BlendTrackList").FirstOrDefault();
                        if (blendList != null)
                        {
                            // Ignore containers which have BlendTrack
                            if (blendList.Elements("BlendTrack").Any())
                                continue;
                        }
                        var blendchildren = blendContainer.Elements("ChildrenList").FirstOrDefault();
                        if(blendchildren == null)
                        {
                            continue;
                        }

                        ConvertBlendContainer(blendContainer, groupId, switchId, workUnitId);
                        changed = true;
                    }

                    if (changed)
                    {
                        var target = options.Overwrite ? path : GetFixedFileName(path);

                        Save(doc, target);

                        Console.WriteLine("Fixed Work Unit written to: " + target);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("Convert Failed: " + ex.Message);
                throw;
            }
        }

        private static string GetFixedFileName(string source)
        {
            var dir = Path.GetDirectoryName(source);
            return Path.Combine(dir, Path.GetFileNameWithoutExtension(source) + "_FIXED.wwu");
        }

        private static void Save(XDocument doc, string path)
        {
            var settings = new XmlWriterSettings();
            settings.Indent = true;
            settings.IndentChars = "\t";  // Use tabs as Wwise does
            settings.Encoding = System.Text.Encoding.ASCII;

            using (var writer = XmlWriter.Create(path, settings))
            {
                doc.Save(writer);
            }
        }

        private static string AddDefaultSwitch(Options options, string groupIDIn, out string groupIdOut, string switchId, out string workUnitId)
        {
            var doc = XDocument.Load(options.SwitchWorkUnitSource);

            var switches = doc.Descendants("Switches").FirstOrDefault();
            if (switches == null)
                throw new InvalidOperationException("Could not find Switches element in switches work unit " + options.SwitchWorkUnitSource);

            var wu = switches.Elements("WorkUnit").FirstOrDefault();
            if (wu == null)
                throw new InvalidOperationException("Could not find WorkUnit element in switches work unit " + options.SwitchWorkUnitSource);

            var childList = wu.Elements("ChildrenList").FirstOrDefault();
            workUnitId = wu.Attribute("ID")?.Value;
            if (string.IsNullOrEmpty(workUnitId))
                throw new InvalidOperationException("Invalid Switch WorkUnitId");

            if (childList == null)
            {
                childList = new XElement("ChildrenList");
                wu.Add(childList);
            }
            else
            {
                var sg = childList.Elements("SwitchGroup").FirstOrDefault();
                if(sg != null)
                {
                    groupIdOut = sg.Attribute("ID").Value;
                    var dsg = sg.Elements("ChildrenList").FirstOrDefault();
                    if(dsg != null)
                    {
                        var sw = dsg.Elements("Switch").FirstOrDefault();
                        if(sw != null)
                        {
                            if(sw.Attribute("Name").Value == "Default")
                            {
                                return sw.Attribute("ID").Value;
                            }
                        }
                    }
                }
            }

            childList.Add(
                new XElement("SwitchGroup",
                    new XAttribute("Name", "Default_Switch_Group"),
                    new XAttribute("ID", groupIDIn),
                    new XElement("ChildrenList",
                        new XElement("Switch",
                            new XAttribute("Name", "Default"),
                            new XAttribute("ID", switchId)
                        ))));

            var target = options.Overwrite ? options.SwitchWorkUnitSource : GetFixedFileName(options.SwitchWorkUnitSource);

            Save(doc, target);

            Console.WriteLine("Fixed Switch Work Unit written to: " + target);

            groupIdOut = groupIDIn;
            return switchId;
        }

        private static void ConvertBlendContainer(XElement blendContainer, string groupId, string switchId, string switchWorkUnitId)
        {
            blendContainer.Name = "SwitchContainer";

            // Add groupingInfo and groupingList
            var groupingInfo =
                new XElement("GroupingInfo",
                    new XElement("GroupingBehaviorList"),
                    new XElement("GroupingList",
                        new XElement("Grouping",
                            new XElement("SwitchRef",
                                new XAttribute("Name", "Default"),
                                new XAttribute("ID", switchId)),
                            new XElement("ItemList")
                        )));

            blendContainer.Add(groupingInfo);

            var groupingBehaviorList = groupingInfo.Descendants("GroupingBehaviorList").First();

            var groupingItemList = groupingInfo.Descendants("ItemList").First();

            // Add switch references
            var refList = blendContainer.Elements("ReferenceList").FirstOrDefault();
            if (refList == null)
            {
                refList = new XElement("ReferenceList");
                blendContainer.Add(refList);
            }

            var switchGroupRef = new XElement("Reference", new XAttribute("Name", "SwitchGroupOrStateGroup"),
                new XElement("ObjectRef", new XAttribute("Name", "Default_Switch_Group"), new XAttribute("ID", groupId), new XAttribute("WorkUnitID", switchWorkUnitId)));

            refList.Add(switchGroupRef);

            var defaultSwitchOrStateRef = new XElement("Reference", new XAttribute("Name", "DefaultSwitchOrState"),
                new XElement("ObjectRef", new XAttribute("Name", "Default"), new XAttribute("ID", switchId), new XAttribute("WorkUnitID", switchWorkUnitId)));

            refList.Add(defaultSwitchOrStateRef);

            // Remove the blend tracks
            var blendList = blendContainer.Elements("BlendTrackList").FirstOrDefault();
            blendList?.Remove();

            var childList = blendContainer.Elements("ChildrenList").FirstOrDefault();

            if (childList == null)
                return;

            foreach (var sound in childList.Elements())
            {
                var name = sound.Attribute("Name");
                var id = sound.Attribute("ID");

                if (name == null || id == null)
                    continue;

                var itemRef = new XElement("ItemRef", new XAttribute(name), new XAttribute(id));

                // Found a sound reference 
                // Creaate a switch grouping
                groupingBehaviorList.Add(new XElement("GroupingBehavior", new XElement(itemRef)));
                groupingItemList.Add(new XElement(itemRef));
            }
        }

        private static Options ParseArgs(string[] args)
        {
            var options = new Options();
            var parser = new ArgParser(args.ToArray());

            parser.AddOption("input", typeof(string), null);
            parser.AddAlias("i", "input");
            parser.AddOption("switch", typeof(string), null);
            parser.AddAlias("s", "switch");
            parser.AddOption("help", typeof(bool), null);
            parser.AddAlias("?", "help");
            parser.AddAlias("h", "help");
            parser.AddOption("overwrite", typeof(bool), null);
            parser.AddAlias("o", "overwrite");

            parser.Parse();

            options.Source = parser["input"] as string;
            options.SwitchWorkUnitSource = parser["switch"] as string;
            options.DisplayHelp = (bool?)parser["help"] == true;
            options.Overwrite = (bool?)parser["overwrite"] == true;

            if (options.DisplayHelp)
            {
                PrintHelp();
            }

            if (options.Source == null || options.SwitchWorkUnitSource == null)
            {
                PrintHelp();
                Environment.Exit(-1);
            }

            return options;
        }

        private static void PrintHelp()
        {
            Assembly asm = Assembly.GetExecutingAssembly();

            Console.WriteLine(asm.GetName().Name + " <options>");
            Console.WriteLine("Version: " + asm.GetName().Version);
            Console.WriteLine("");
            Console.WriteLine("  -?,  -help                           Displays this help message");
            Console.WriteLine("  -i,  -input:<path.wwu>               The input work unit file name or directory name to scan for work units");
            Console.WriteLine("  -s,  -switch:<path.wwu>              The Wwise Switches work unit path");
            Console.WriteLine("  -o,  -overwrite                      Overwrite original work unit files");
            Console.WriteLine("");
            Console.WriteLine("Example:  WwiseBlendFix -i C:/Proj/Actor-Mixer Hierarchy/Default Work Unit.wwu -s C:/Proj/Switches/Default Work Unit.wwu");
            Console.WriteLine("");
        }

        private class Options
        {
            public string Source { get; set; }
            public string SwitchWorkUnitSource { get; set; }
            public bool DisplayHelp { get; set; }
            public bool Overwrite { get; set; }
        }
    }

    public class ArgParserException : Exception
    {
        public ArgParserException(string message) : base(message) { }
    }

    public class ArgParser
    {
        public ArgParser(string[] args)
        {
            _args = args;
        }

        public void AddOption(string name, Type type, object defaultValue)
        {
            _options[name] = NewOption(type, defaultValue);
        }

        public void AddAlias(string aliasName, string optionName)
        {
            System.Diagnostics.Debug.Assert(_options.ContainsKey(optionName));
            _options[aliasName] = _options[optionName];
        }

        public void Parse()
        {
            List<string> extras = new List<string>();
            for (int i = 0; i < _args.Length; ++i)
            {
                string arg = _args[i];
                if (arg[0] == '-' || arg[0] == '/') // it's an option
                {
                    if (arg.Length == 1)
                        throw new ArgParserException(String.Format("Couldn't parse argument \"{0}\"", arg));
                    IOption opt = (IOption)_options[arg.Substring(1)];
                    if (opt == null)
                        throw new ArgParserException(String.Format("Couldn't parse argument \"{0}\"", arg));
                    i = opt.Set(_args, i);
                }
                else
                {
                    extras.Add(arg);
                }
            }

            _extraArgs = extras;
        }

        public object this[string name]
        {
            get
            {
                IOption opt = (IOption)_options[name];
                if (opt == null)
                    return null;
                return opt.Value;
            }
        }

        public IList<string> ExtraArgs
        {
            get { return _extraArgs; }
        }

        #region Option classes

        private interface IOption
        {
            int Set(string[] args, int i);

            object Value { get; }
        }

        private class GenericOption : IOption
        {
            public GenericOption(Type type, object defaultValue)
            {
                _type = type;
                _value = defaultValue;
            }

            public int Set(string[] args, int i)
            {
                if (i >= args.Length - 1)
                    throw new ArgParserException(string.Format("\"{0}\" argument requires a value", args[0]));

                string value = args[i + 1];
                TypeConverter converter = TypeDescriptor.GetConverter(_type);
                try
                {
                    _value = converter.ConvertFromString(value);
                }

                catch (Exception ex)
                {
                    throw new ArgParserException(string.Format("Couldn't parse value \"{0}\" for argument \"{1}\"", value, args[i]));
                }

                return i + 1;
            }


            public object Value
            {
                get { return _value; }
            }

            private Type _type;
            private object _value;
        }

        private class BoolOption : IOption
        {
            public BoolOption(object defaultValue)
            {
                _value = defaultValue;
            }

            public int Set(string[] args, int i)
            {
                _value = true;
                return i;
            }

            public object Value
            {
                get { return _value; }
            }

            private object _value;
        }

        #endregion

        private string[] _args;
        private IList<string> _extraArgs;
        private Hashtable _options = new Hashtable();

        private IOption NewOption(Type type, object defaultValue)
        {
            if (type == typeof(bool))
                return new BoolOption(defaultValue);
            else
                return new GenericOption(type, defaultValue);
        }
    }
}