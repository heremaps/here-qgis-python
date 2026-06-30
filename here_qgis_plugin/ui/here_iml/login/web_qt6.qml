/**
 *
 * Copyright (c) 2023 HERE Europe B.V.
 *
 * SPDX-License-Identifier: MIT
 * License-Filename: LICENSE
 *
 */
import QtQuick 2.10
import QtQuick.Window 2.10
import QtQml 2.10
import QtWebEngine 2

// https://doc.qt.io/qt-5/qml-qtwebengine-webengineview.html#newViewRequested-signal
// https://doc.qt.io/qt-6/qml-qtwebengine-webengineview.html#newWindowRequested-signal
Item {
    id: windowParent

    // Configuration properties
    property string loginUrl: "https://platform.here.com"
    property int initialWidth: 600
    property int initialHeight: 600
    property string debugMode: ""
    property string flagLogoutAndReload: ""
    property string flagLogoutAndClose: ""

    // State properties
    property string tokenJson: ""
    property string error: ""
    property string loggingText: ""

    width: initialWidth
    height: initialHeight

    // connect signal of main webView
    Connections {
        target: webView

        Component.onCompleted: {
            saveLogFile()
        }

        function onWindowCloseRequested(event) {
        }

        function onLoadingChanged(loadRequest) {
            //if (loadRequest.status == WebEngineView.LoadStartedStatus) {
            //    return
            //}

            let currentUrl = loadRequest.url.toString().replace(/\/$/, "")
            let targetUrl = loginUrl.replace(/\/$/, "")

            if (currentUrl == targetUrl || currentUrl == targetUrl + "/portal") {
                if (loadRequest.status == WebEngineView.LoadSucceededStatus) {
                    logoutAndReload().then(logoutAndClose).then(refreshTokenAndClose)
                }
            }
        }
    }

    Connections {
        target: windowParent.Window.window

        function onClosing(event) {
            saveLogFile()
        }
    }

    function closeWindow(item) {
        item.Window.window.close()
    }

    // Logging functions
    function isDebug() { return debugMode != "" }

    function logText(txt) {
        loggingText += "\n" + ("<p>" + txt + "</p>").replace(/\n/g, "\n<br>")
        console.log("" + txt)
    }

    function cbConsoleLog(level, message, lineNumber, sourceId) {
        let levels = ["INFO", "WARN", "ERROR"]
        logText(levels[level] + " - " + message + " - " + sourceId + ":" + lineNumber)
    }

    function saveLogFile() {
        function _saveLogFile(fileUrl, text) {
            if (!isDebug())
                return
            logText("saving log to " + fileUrl)
            var request = new XMLHttpRequest()
            request.open("PUT", fileUrl, false)
            request.send(text)
            return request.status
        }
        if (isDebug()) {
            _saveLogFile(Qt.resolvedUrl("log.html"), loggingText)
        }
    }

    // Token management

    function getToken() { return tokenJson }
    function getError() { return error }
    function getLogging() { return loggingText }

    function runScriptAsync(cmd) {
        return new Promise(function(resolve, reject) {
            webView.runJavaScript(cmd, function(resp){
                if ( !resp ) reject(new Error(resp));
                else if (resp.error) reject(resp.error);
                else resolve(resp);
            });
        });
    }

    function refreshTokenAndClose() {
        return refreshTokenAsync().then(closeWebView)
    }

    function getTokenAgain() {
        refreshTokenAsync()
        return tokenJson
    }

    function refreshTokenAsync() {
        logText("refreshTokenAsync")
        let cmd = 'hasTokenSync();'
        return runScriptAsync(cmd)
            .then(function(resp){
                logText("refreshToken " + JSON.stringify(resp))
                return resp
            })
            .then(handleTokenOutput)
            .catch((err) => {
                logText("refreshToken error: " + JSON.stringify(err))
                error = err
                throw err
            })
    }

    function handleTokenOutput(output) {
        function saveToken(response) {
            logText(response)
            logText(JSON.parse(response).accessToken)
            tokenJson = response
        }
        if (!output) {
            return
        }
        if (output.response) {
            saveToken(output.response)
        }
        return tokenJson
    }

    function logoutAsync() {
        logText("logout")
        let cmd = 'logoutSync()'
        return runScriptAsync(cmd).then(function(resp){
            logText("logout " + JSON.stringify(resp))
            return resp
        })
        .catch((err) => {
            logText("logout error: " + JSON.stringify(err))
            error = err
        })
    }

    function logoutAndClose() {
        if (flagLogoutAndClose == "true") {
            return finallyCloseWebView(
                logoutAsync().then(function(resp) {
                    logText("logoutAndClose " + resp)
                    if (resp) {
                        flagLogoutAndClose = ""
                    }
                    return resp
                })
            )
        }
        return Promise.resolve()
    }

    function logoutAndReload() {
        if (flagLogoutAndReload == "true") {
            return logoutAsync().then(function(resp) {
                if (resp) {
                    flagLogoutAndReload = ""
                    webView.reload()
                }
                return resp
            })
        }
        return Promise.resolve()
    }

    function closeWebView() {
        logText("close webView")
        webView.windowCloseRequested()
    }

    function finallyCloseWebView( asyncFn ) {
        return Promise.resolve().then(asyncFn)
            .then(closeWebView)
            .catch(closeWebView)
    }

    // profile

    function getProfilePath() {
        return WebEngine.defaultProfile.persistentStoragePath
    }

    // Web components

    property WebEngineView webView: {
        init_config(WebEngine.defaultProfile, WebEngine.settings)
        webViewComponent.createObject(windowParent, {
            "url": loginUrl
        })
    }

    function init_config(web_profile, web_settings) {
        web_settings.javascriptEnabled = true
        web_profile.userScripts.collection = [{
            injectionPoint: WebEngineScript.DocumentCreation,
            worldId: WebEngineScript.MainWorld,
            sourceUrl: Qt.resolvedUrl("web.js"),
        }]

        //if (flagLogoutAndClose == "true") web_profile.persistentCookiesPolicy = WebEngineProfile.NoPersistentCookies

        //offTheRecord not reset session cookie
        //web_profile.offTheRecord = true
        //web_profile.persistentCookiesPolicy = WebEngineProfile.NoPersistentCookies
        //set storageName (profile name)
        //let cookieId = 0
        //let name = cookieId == 0 ? "Default" : "tmp-" + cookieId
        //web_profile.storageName = name
        //web_profile.persistentCookiesPolicy = WebEngineProfile.ForcePersistentCookies
    }

    property Component webViewComponent: WebEngineView {
        anchors.fill: parent

        Component.onCompleted: {

            // this.profile.offTheRecord = true
            // this.profile.persistentCookiesPolicy = WebEngineProfile.NoPersistentCookies // use new cookies everytime
            // this.settings.javascriptEnabled = true

            //logText(JSON.stringify({
            //    offTheRecord: this.profile.offTheRecord,
            //    storageName: this.profile.storageName,
            //    persistentStoragePath: this.profile.persistentStoragePath,
            //    persistentCookiesPolicy: this.profile.persistentCookiesPolicy,
            //    httpUserAgent: this.profile.httpUserAgent,
            //}, null, 2))
            //logText(JSON.stringify({
            //    javascriptEnabled : this.settings.javascriptEnabled,
            //    localContentCanAccessFileUrls : this.settings.localContentCanAccessFileUrls,
            //    localContentCanAccessRemoteUrls : this.settings.localContentCanAccessRemoteUrls,
            //    localStorageEnabled : this.settings.localStorageEnabled,
            //    allowRunningInsecureContent : this.settings.allowRunningInsecureContent,
            //    unknownUrlSchemePolicy  : this.settings.unknownUrlSchemePolicy ,
            //    webGLEnabled  : this.settings.webGLEnabled ,
            //    webRTCPublicInterfacesOnly : this.settings.webRTCPublicInterfacesOnly,
            //    accelerated2dCanvasEnabled  : this.settings.accelerated2dCanvasEnabled ,
            //}, null, 2))

            // this.javaScriptConsoleMessage.connect(cbConsoleLog)
            // // show webview settings
            // logText("settings " + Object.keys(this.settings)
            // .filter((k) => typeof this.settings[k] != 'function')
            // .map((k) => "<br> >>" + k + ": " + this.settings[k]).join(""))
        }

        onRenderProcessTerminated: function (terminationStatus, exitCode) {
            logText("terminationStatus: " + terminationStatus + " exitCode: " + "<br> >> ")
        }

        onNewWindowRequested: function(request) {
            let newWindow = windowComponent.createObject(windowParent)
            request.openIn(newWindow.webView)
        }

        onCertificateError: function (error) {
            logText("certificateError description: " + error.description + " error: " + error.error
                    + " overridable: " + error.overridable + "<br> >> " + error.url)
            error.ignoreCertificateError() // ignore cert error
        }

        onLoadingChanged: function(loadRequest) {
            logText("loadRequest errorDomain: " + loadRequest.errorDomain
                    + " errorString: " + loadRequest.errorString + " status: "
                    + loadRequest.status + "<br> >> " + loadRequest.url)
        }

        onWindowCloseRequested: closeWindow(this)
    }

    property Component windowComponent: Window {
        // Destroy on close to release the Window's QML resources.
        // Because it was created with a parent, it won't be garbage-collected.
        onClosing: destroy()
        visible: true
        width: initialWidth
        height: initialHeight
        title: webView.title
        modality: parent.Window ? parent.Window.window.modality : Qt.WindowModality.ApplicationModal

        property WebEngineView webView: webViewComponent.createObject(this)
    }
}
