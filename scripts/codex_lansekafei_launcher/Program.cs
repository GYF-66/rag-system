using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

namespace CodexLansekafeiLauncher
{
    internal static class Program
    {
        private static string LoadOpenAiKeyFromDotEnv(string projectRoot)
        {
            var envPath = Path.Combine(projectRoot, ".env");
            if (!File.Exists(envPath))
            {
                return null;
            }

            foreach (var rawLine in File.ReadLines(envPath, Encoding.UTF8))
            {
                var line = rawLine.Trim();
                if (string.IsNullOrWhiteSpace(line) || line.StartsWith("#", StringComparison.Ordinal))
                {
                    continue;
                }

                var separatorIndex = line.IndexOf('=');
                if (separatorIndex <= 0)
                {
                    continue;
                }

                var key = line.Substring(0, separatorIndex).Trim();
                if (!string.Equals(key, "OPENAI_API_KEY", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                return line.Substring(separatorIndex + 1).Trim();
            }

            return null;
        }

        public static int Main(string[] args)
        {
            var scriptDir = AppContext.BaseDirectory;
            var projectRoot = Path.GetFullPath(Path.Combine(scriptDir, "..", "..", "..", ".."));
            var npxPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                "nodejs",
                "npx.cmd"
            );
            var openAiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY");
            if (string.IsNullOrWhiteSpace(openAiKey))
            {
                openAiKey = LoadOpenAiKeyFromDotEnv(projectRoot);
            }

            if (string.IsNullOrWhiteSpace(openAiKey))
            {
                Console.Error.WriteLine("Missing OPENAI_API_KEY environment variable.");
                return 1;
            }
            if (!File.Exists(npxPath))
            {
                Console.Error.WriteLine("Missing npx.cmd: " + npxPath);
                return 1;
            }

            var codexArgs = new List<string>
            {
                "-y",
                "@openai/codex@0.57.0",
                "-c", "model_provider=\"lansekafei\"",
                "-c", "model=\"qwen3-coder-plus\"",
                "-c", "model_providers.lansekafei.name=\"Lansekafei\"",
                "-c", "model_providers.lansekafei.base_url=\"https://www.lansekafei.asia/v1\"",
                "-c", "model_providers.lansekafei.env_key=\"OPENAI_API_KEY\"",
                "-c", "model_providers.lansekafei.wire_api=\"chat\"",
                "-c", "model_providers.lansekafei.requires_openai_auth=false"
            };
            codexArgs.AddRange(args);

            var psi = new ProcessStartInfo
            {
                FileName = npxPath,
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                WorkingDirectory = projectRoot,
            };

            foreach (var arg in codexArgs)
            {
                psi.Arguments += (psi.Arguments.Length == 0 ? "" : " ") + Quote(arg);
            }

            psi.EnvironmentVariables["OPENAI_API_KEY"] = openAiKey;

            using (var process = new Process())
            {
                process.StartInfo = psi;
                process.Start();

                using (var stdout = OpenStandardWriteStream(-11))
                using (var stderr = OpenStandardWriteStream(-12))
                using (var stdin = OpenStandardReadStream(-10))
                {
                    var stdoutTask = process.StandardOutput.BaseStream.CopyToAsync(stdout);
                    var stderrTask = process.StandardError.BaseStream.CopyToAsync(stderr);
                    var stdinTask = stdin.CopyToAsync(process.StandardInput.BaseStream).ContinueWith(delegate
                    {
                        try
                        {
                            process.StandardInput.Close();
                        }
                        catch
                        {
                        }
                    });

                    Task.WaitAll(stdoutTask, stderrTask, stdinTask, Task.Run(delegate { process.WaitForExit(); }));
                    return process.ExitCode;
                }
            }
        }

        private static FileStream OpenStandardWriteStream(int stdHandle)
        {
            var handle = GetStdHandle(stdHandle);
            return new FileStream(new Microsoft.Win32.SafeHandles.SafeFileHandle(handle, ownsHandle: false), FileAccess.Write);
        }

        private static FileStream OpenStandardReadStream(int stdHandle)
        {
            var handle = GetStdHandle(stdHandle);
            return new FileStream(new Microsoft.Win32.SafeHandles.SafeFileHandle(handle, ownsHandle: false), FileAccess.Read);
        }

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr GetStdHandle(int nStdHandle);

        private static string Quote(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return "\"\"";
            }

            return value.IndexOf(' ') >= 0 || value.IndexOf('"') >= 0
                ? "\"" + value.Replace("\"", "\\\"") + "\""
                : value;
        }
    }
}
