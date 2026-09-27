#include <windows.h>
#include <userenv.h>
#include <sddl.h>

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string Narrow(const std::wstring& value) {
    if (value.empty()) return {};
    int count = WideCharToMultiByte(CP_UTF8, 0, value.data(),
                                    static_cast<int>(value.size()), nullptr, 0,
                                    nullptr, nullptr);
    std::string result(static_cast<size_t>(count), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.data(), static_cast<int>(value.size()),
                        result.data(), count, nullptr, nullptr);
    return result;
}

std::string JsonEscape(const std::string& value) {
    std::ostringstream out;
    for (unsigned char ch : value) {
        switch (ch) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (ch < 0x20) {
                    const char* hex = "0123456789abcdef";
                    out << "\\u00" << hex[ch >> 4] << hex[ch & 0x0f];
                } else {
                    out << static_cast<char>(ch);
                }
        }
    }
    return out.str();
}

std::string SidText(PSID sid) {
    if (!sid || !IsValidSid(sid)) return {};
    LPWSTR raw = nullptr;
    if (!ConvertSidToStringSidW(sid, &raw)) return {};
    std::wstring value(raw);
    LocalFree(raw);
    return Narrow(value);
}

struct TokenEvidence {
    bool query_ok = false;
    DWORD query_error = ERROR_SUCCESS;
    bool is_appcontainer = false;
    bool elevated = false;
    std::string appcontainer_sid;
};

TokenEvidence InspectToken(HANDLE process) {
    TokenEvidence evidence;
    HANDLE token = nullptr;
    if (!OpenProcessToken(process, TOKEN_QUERY, &token)) {
        evidence.query_error = GetLastError();
        return evidence;
    }
    DWORD is_appcontainer = 0;
    DWORD returned = 0;
    TOKEN_ELEVATION elevation{};
    bool app_ok = GetTokenInformation(token, TokenIsAppContainer,
                                      &is_appcontainer, sizeof(is_appcontainer),
                                      &returned) != FALSE;
    DWORD app_error = app_ok ? ERROR_SUCCESS : GetLastError();
    bool elevation_ok = GetTokenInformation(token, TokenElevation, &elevation,
                                            sizeof(elevation), &returned) != FALSE;
    DWORD elevation_error = elevation_ok ? ERROR_SUCCESS : GetLastError();

    DWORD needed = 0;
    GetTokenInformation(token, TokenAppContainerSid, nullptr, 0, &needed);
    DWORD sid_probe_error = GetLastError();
    std::vector<BYTE> buffer(needed ? needed : sizeof(TOKEN_APPCONTAINER_INFORMATION));
    bool sid_ok = false;
    if (needed && sid_probe_error == ERROR_INSUFFICIENT_BUFFER) {
        sid_ok = GetTokenInformation(token, TokenAppContainerSid, buffer.data(),
                                     static_cast<DWORD>(buffer.size()), &returned) != FALSE;
        if (sid_ok) {
            auto* info = reinterpret_cast<TOKEN_APPCONTAINER_INFORMATION*>(buffer.data());
            evidence.appcontainer_sid = SidText(info->TokenAppContainer);
        }
    }
    DWORD sid_error = sid_ok || (!is_appcontainer && needed == 0)
                          ? ERROR_SUCCESS : GetLastError();
    CloseHandle(token);
    evidence.query_ok = app_ok && elevation_ok && (sid_ok || !is_appcontainer);
    evidence.query_error = !app_ok ? app_error : !elevation_ok ? elevation_error : sid_error;
    evidence.is_appcontainer = is_appcontainer != 0;
    evidence.elevated = elevation.TokenIsElevated != 0;
    return evidence;
}

bool ChildHasHandle(HANDLE child_process, HANDLE candidate) {
    HANDLE duplicate = nullptr;
    if (!DuplicateHandle(child_process, candidate, GetCurrentProcess(), &duplicate,
                         0, FALSE, DUPLICATE_SAME_ACCESS)) {
        return false;
    }
    CloseHandle(duplicate);
    return true;
}

struct LaunchResult {
    std::string name;
    bool use_extended = false;
    bool use_appcontainer = false;
    bool use_handle_list = false;
    DWORD attribute_count = 0;
    BOOL sizing_return = FALSE;
    DWORD sizing_error = ERROR_SUCCESS;
    SIZE_T attribute_bytes = 0;
    BOOL initialize_return = FALSE;
    DWORD initialize_error = ERROR_SUCCESS;
    BOOL security_update_return = FALSE;
    DWORD security_update_error = ERROR_SUCCESS;
    BOOL handle_update_return = FALSE;
    DWORD handle_update_error = ERROR_SUCCESS;
    DWORD startup_cb = 0;
    BOOL inherit_handles = FALSE;
    DWORD creation_flags = 0;
    BOOL create_return = FALSE;
    DWORD create_error = ERROR_SUCCESS;
    DWORD pid = 0;
    bool allowed_inherited = false;
    bool decoy_inherited = false;
    TokenEvidence token;
};

LaunchResult RunExperiment(const std::string& name,
                           const std::wstring& executable,
                           PSID appcontainer_sid,
                           bool use_appcontainer,
                           bool use_handle_list,
                           HANDLE allowed_handle,
                           HANDLE decoy_handle) {
    LaunchResult result;
    result.name = name;
    result.use_extended = use_appcontainer || use_handle_list;
    result.use_appcontainer = use_appcontainer;
    result.use_handle_list = use_handle_list;
    result.attribute_count = static_cast<DWORD>(use_appcontainer) +
                             static_cast<DWORD>(use_handle_list);
    result.inherit_handles = use_handle_list ? TRUE : FALSE;
    result.creation_flags = CREATE_SUSPENDED |
        (result.use_extended ? EXTENDED_STARTUPINFO_PRESENT : 0);

    STARTUPINFOEXW startup{};
    startup.StartupInfo.cb = result.use_extended
        ? sizeof(STARTUPINFOEXW)
        : sizeof(STARTUPINFOW);
    result.startup_cb = startup.StartupInfo.cb;

    SIZE_T attribute_bytes = 0;
    std::vector<BYTE> attribute_storage;
    LPPROC_THREAD_ATTRIBUTE_LIST attributes = nullptr;
    SECURITY_CAPABILITIES security{};
    HANDLE handle_list[1] = {allowed_handle};

    if (result.use_extended) {
        SetLastError(ERROR_SUCCESS);
        result.sizing_return = InitializeProcThreadAttributeList(
            nullptr, result.attribute_count, 0, &attribute_bytes);
        result.sizing_error = GetLastError();
        result.attribute_bytes = attribute_bytes;
        attribute_storage.resize(attribute_bytes);
        attributes = reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(
            attribute_storage.data());
        SetLastError(ERROR_SUCCESS);
        result.initialize_return = InitializeProcThreadAttributeList(
            attributes, result.attribute_count, 0, &attribute_bytes);
        result.initialize_error = result.initialize_return
            ? ERROR_SUCCESS : GetLastError();

        if (result.initialize_return && use_appcontainer) {
            security.AppContainerSid = appcontainer_sid;
            security.Capabilities = nullptr;
            security.CapabilityCount = 0;
            security.Reserved = 0;
            SetLastError(ERROR_SUCCESS);
            result.security_update_return = UpdateProcThreadAttribute(
                attributes, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                &security, sizeof(security), nullptr, nullptr);
            result.security_update_error = result.security_update_return
                ? ERROR_SUCCESS : GetLastError();
        }
        if (result.initialize_return && use_handle_list) {
            SetLastError(ERROR_SUCCESS);
            result.handle_update_return = UpdateProcThreadAttribute(
                attributes, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                handle_list, sizeof(handle_list), nullptr, nullptr);
            result.handle_update_error = result.handle_update_return
                ? ERROR_SUCCESS : GetLastError();
        }
        startup.lpAttributeList = attributes;
    }

    std::vector<wchar_t> command(executable.begin(), executable.end());
    command.push_back(L'\0');
    PROCESS_INFORMATION process{};
    SetLastError(ERROR_SUCCESS);
    result.create_return = CreateProcessW(
        executable.c_str(), command.data(), nullptr, nullptr,
        result.inherit_handles, result.creation_flags, nullptr, nullptr,
        reinterpret_cast<LPSTARTUPINFOW>(&startup), &process);
    result.create_error = result.create_return ? ERROR_SUCCESS : GetLastError();

    if (result.create_return) {
        result.pid = process.dwProcessId;
        result.token = InspectToken(process.hProcess);
        if (use_handle_list) {
            result.allowed_inherited = ChildHasHandle(process.hProcess, allowed_handle);
            result.decoy_inherited = ChildHasHandle(process.hProcess, decoy_handle);
        }
        TerminateProcess(process.hProcess, 0);
        WaitForSingleObject(process.hProcess, 5000);
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
    }
    if (attributes) DeleteProcThreadAttributeList(attributes);
    return result;
}

void PrintResult(const LaunchResult& r, const std::string& executable) {
    std::cout
        << "{\"type\":\"experiment\",\"name\":\"" << r.name
        << "\",\"api\":\"CreateProcessW\",\"executable\":\"" << JsonEscape(executable)
        << "\",\"use_extended\":" << (r.use_extended ? "true" : "false")
        << ",\"use_appcontainer\":" << (r.use_appcontainer ? "true" : "false")
        << ",\"use_handle_list\":" << (r.use_handle_list ? "true" : "false")
        << ",\"attribute_count\":" << r.attribute_count
        << ",\"attribute_bytes\":" << r.attribute_bytes
        << ",\"sizing_return\":" << (r.sizing_return ? "true" : "false")
        << ",\"sizing_error\":" << r.sizing_error
        << ",\"initialize_return\":" << (r.initialize_return ? "true" : "false")
        << ",\"initialize_error\":" << r.initialize_error
        << ",\"security_update_return\":" << (r.security_update_return ? "true" : "false")
        << ",\"security_update_error\":" << r.security_update_error
        << ",\"handle_update_return\":" << (r.handle_update_return ? "true" : "false")
        << ",\"handle_update_error\":" << r.handle_update_error
        << ",\"startup_cb\":" << r.startup_cb
        << ",\"inherit_handles\":" << (r.inherit_handles ? "true" : "false")
        << ",\"creation_flags\":" << r.creation_flags
        << ",\"create_return\":" << (r.create_return ? "true" : "false")
        << ",\"create_error\":" << r.create_error
        << ",\"pid\":" << r.pid
        << ",\"token_query_ok\":" << (r.token.query_ok ? "true" : "false")
        << ",\"token_query_error\":" << r.token.query_error
        << ",\"token_is_appcontainer\":" << (r.token.is_appcontainer ? "true" : "false")
        << ",\"token_elevated\":" << (r.token.elevated ? "true" : "false")
        << ",\"token_appcontainer_sid\":\"" << JsonEscape(r.token.appcontainer_sid)
        << "\",\"allowed_handle_inherited\":" << (r.allowed_inherited ? "true" : "false")
        << ",\"decoy_handle_inherited\":" << (r.decoy_inherited ? "true" : "false")
        << "}\n";
}

}  // namespace

int wmain() {
    wchar_t system_directory[MAX_PATH]{};
    UINT system_length = GetSystemDirectoryW(system_directory, MAX_PATH);
    if (!system_length || system_length >= MAX_PATH) return 2;
    std::wstring executable = std::wstring(system_directory) + L"\\whoami.exe";

    BOOL in_job = FALSE;
    BOOL job_query_ok = IsProcessInJob(GetCurrentProcess(), nullptr, &in_job);
    DWORD job_query_error = job_query_ok ? ERROR_SUCCESS : GetLastError();

    auto tick = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::wstring profile_name = L"mke.s4b2.p0r1.native." +
        std::to_wstring(GetCurrentProcessId()) + L"." + std::to_wstring(tick);
    PSID profile_sid = nullptr;
    HRESULT create_hr = CreateAppContainerProfile(
        profile_name.c_str(), L"MKE S4-B2 P0-R1", L"Disposable native diagnosis",
        nullptr, 0, &profile_sid);

    SECURITY_ATTRIBUTES inheritable{};
    inheritable.nLength = sizeof(inheritable);
    inheritable.bInheritHandle = TRUE;
    HANDLE allowed = CreateEventW(&inheritable, TRUE, FALSE, nullptr);
    HANDLE decoy = CreateEventW(&inheritable, TRUE, FALSE, nullptr);
    DWORD allowed_flags = 0;
    DWORD decoy_flags = 0;
    BOOL allowed_info = GetHandleInformation(allowed, &allowed_flags);
    BOOL decoy_info = GetHandleInformation(decoy, &decoy_flags);

    std::cout
        << "{\"type\":\"metadata\",\"pointer_size\":" << sizeof(void*)
        << ",\"sizeof_STARTUPINFOW\":" << sizeof(STARTUPINFOW)
        << ",\"alignof_STARTUPINFOW\":" << alignof(STARTUPINFOW)
        << ",\"sizeof_STARTUPINFOEXW\":" << sizeof(STARTUPINFOEXW)
        << ",\"alignof_STARTUPINFOEXW\":" << alignof(STARTUPINFOEXW)
        << ",\"offsetof_dwXCountChars\":" << offsetof(STARTUPINFOW, dwXCountChars)
        << ",\"offsetof_dwYCountChars\":" << offsetof(STARTUPINFOW, dwYCountChars)
        << ",\"offsetof_dwFillAttribute\":" << offsetof(STARTUPINFOW, dwFillAttribute)
        << ",\"offsetof_lpAttributeList\":" << offsetof(STARTUPINFOEXW, lpAttributeList)
        << ",\"sizeof_SECURITY_CAPABILITIES\":" << sizeof(SECURITY_CAPABILITIES)
        << ",\"alignof_SECURITY_CAPABILITIES\":" << alignof(SECURITY_CAPABILITIES)
        << ",\"sizeof_HANDLE\":" << sizeof(HANDLE)
        << ",\"process_in_job_query_ok\":" << (job_query_ok ? "true" : "false")
        << ",\"process_in_job\":" << (in_job ? "true" : "false")
        << ",\"process_in_job_error\":" << job_query_error
        << ",\"profile_create_hresult\":" << static_cast<uint32_t>(create_hr)
        << ",\"profile_sid_valid\":" << (profile_sid && IsValidSid(profile_sid) ? "true" : "false")
        << ",\"profile_sid\":\"" << JsonEscape(SidText(profile_sid))
        << "\",\"allowed_handle_value\":" << reinterpret_cast<uintptr_t>(allowed)
        << ",\"allowed_handle_info_ok\":" << (allowed_info ? "true" : "false")
        << ",\"allowed_handle_flags\":" << allowed_flags
        << ",\"decoy_handle_value\":" << reinterpret_cast<uintptr_t>(decoy)
        << ",\"decoy_handle_info_ok\":" << (decoy_info ? "true" : "false")
        << ",\"decoy_handle_flags\":" << decoy_flags
        << ",\"executable\":\"" << JsonEscape(Narrow(executable)) << "\"}\n";

    if (FAILED(create_hr) || !profile_sid || !allowed || !decoy) {
        if (allowed) CloseHandle(allowed);
        if (decoy) CloseHandle(decoy);
        if (profile_sid) FreeSid(profile_sid);
        DeleteAppContainerProfile(profile_name.c_str());
        return 3;
    }

    std::vector<LaunchResult> results;
    results.push_back(RunExperiment("A_normal", executable, profile_sid, false, false, allowed, decoy));
    results.push_back(RunExperiment("B_appcontainer_only", executable, profile_sid, true, false, allowed, decoy));
    results.push_back(RunExperiment("C_handle_list_only", executable, profile_sid, false, true, allowed, decoy));
    results.push_back(RunExperiment("D_combined", executable, profile_sid, true, true, allowed, decoy));
    for (const auto& result : results) PrintResult(result, Narrow(executable));

    CloseHandle(allowed);
    CloseHandle(decoy);
    FreeSid(profile_sid);
    HRESULT delete_hr = DeleteAppContainerProfile(profile_name.c_str());
    std::cout << "{\"type\":\"cleanup\",\"profile_delete_hresult\":"
              << static_cast<uint32_t>(delete_hr) << "}\n";
    return 0;
}
