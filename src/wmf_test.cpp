#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

static double get_time_ms() {
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart * 1000.0 / (double)freq.QuadPart;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("{\"error\": \"Usage: wmf_test.exe <URL> [--json]\"}\n");
        return 1;
    }

    const char* url_mb = argv[1];
    int json_mode = 0;
    if (argc >= 3 && strcmp(argv[2], "--json") == 0) {
        json_mode = 1;
    }

    wchar_t url_wc[2048];
    MultiByteToWideChar(CP_UTF8, 0, url_mb, -1, url_wc, 2048);

    double start_total = get_time_ms();
    
    HRESULT hr_coinit = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    (void)hr_coinit;
    
    double start_mf = get_time_ms();
    HRESULT hr_mfstart = MFStartup(MF_VERSION, MFSTARTUP_FULL);
    double mf_startup_ms = get_time_ms() - start_mf;

    HRESULT hr_resolver_create = S_OK;
    HRESULT hr_resolver_op = S_OK;
    double resolver_ms = 0.0;
    int resolver_success = 0;
    int object_type = 0;
    (void)object_type;

    IMFSourceResolver* pResolver = NULL;
    hr_resolver_create = MFCreateSourceResolver(&pResolver);
    if (SUCCEEDED(hr_resolver_create) && pResolver) {
        MF_OBJECT_TYPE ObjType = MF_OBJECT_INVALID;
        IUnknown* pSource = NULL;

        double start_res_op = get_time_ms();
        hr_resolver_op = pResolver->CreateObjectFromURL(
            url_wc,
            MF_RESOLUTION_MEDIASOURCE,
            NULL,
            &ObjType,
            &pSource
        );
        resolver_ms = get_time_ms() - start_res_op;

        if (SUCCEEDED(hr_resolver_op)) {
            resolver_success = 1;
            object_type = (int)ObjType;
            if (pSource) pSource->Release();
        }
        pResolver->Release();
    } else {
        hr_resolver_op = hr_resolver_create;
    }

    HRESULT hr_reader_op = S_OK;
    double reader_ms = 0.0;
    int reader_success = 0;

    IMFSourceReader* pReader = NULL;
    double start_read_op = get_time_ms();
    hr_reader_op = MFCreateSourceReaderFromURL(url_wc, NULL, &pReader);
    reader_ms = get_time_ms() - start_read_op;

    if (SUCCEEDED(hr_reader_op) && pReader) {
        reader_success = 1;
        pReader->Release();
    }

    if (SUCCEEDED(hr_mfstart)) {
        MFShutdown();
    }
    CoUninitialize();

    double total_ms = get_time_ms() - start_total;

    if (json_mode) {
        printf("{\n");
        printf("  \"url\": \"%s\",\n", url_mb);
        printf("  \"mf_startup_ms\": %.2f,\n", mf_startup_ms);
        printf("  \"resolver_ms\": %.2f,\n", resolver_ms);
        printf("  \"resolver_success\": %s,\n", resolver_success ? "true" : "false");
        printf("  \"resolver_hresult\": \"0x%08X\",\n", (unsigned int)hr_resolver_op);
        printf("  \"reader_ms\": %.2f,\n", reader_ms);
        printf("  \"reader_success\": %s,\n", reader_success ? "true" : "false");
        printf("  \"reader_hresult\": \"0x%08X\",\n", (unsigned int)hr_reader_op);
        printf("  \"total_ms\": %.2f\n", total_ms);
        printf("}\n");
    } else {
        printf("====================================================\n");
        printf(" [WMF Test Results] URL: %s\n", url_mb);
        printf("====================================================\n");
        printf(" MFStartup Time        : %.2f ms\n", mf_startup_ms);
        printf(" IMFSourceResolver     : %s (HRESULT: 0x%08X, Time: %.2f ms)\n",
               resolver_success ? "SUCCESS" : "FAILED", (unsigned int)hr_resolver_op, resolver_ms);
        printf(" MFCreateSourceReader  : %s (HRESULT: 0x%08X, Time: %.2f ms)\n",
               reader_success ? "SUCCESS" : "FAILED", (unsigned int)hr_reader_op, reader_ms);
        printf(" Total Execution Time  : %.2f ms\n", total_ms);
        printf("====================================================\n");
    }

    return (resolver_success && reader_success) ? 0 : 1;
}
