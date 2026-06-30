/**
 *
 * Copyright (c) 2023 HERE Europe B.V.
 *
 * SPDX-License-Identifier: MIT
 * License-Filename: LICENSE
 *
 */

function makeRequestSync(method, url, data, token) {
    var xhr = new XMLHttpRequest()
    xhr.open(method, url, false)

    if (method === 'POST') {
        xhr.setRequestHeader('Content-Type', 'application/json')
    }

    if (token) {
        xhr.setRequestHeader("Authorization", "Bearer " + token)
    }
    // xhr.withCredentials = true
    xhr.send(data)

    if (xhr.status >= 200 && xhr.status < 300) {
        return xhr.responseText
    } else {
        throw new Error(xhr.statusText)
    }
}

function hasTokenSync(baseUrl="https://platform.here.com") {
    let output = {}
    try {
        var response = makeRequestSync(
                    "GET", baseUrl + "/api/portal/accessToken",
                    null, null)
        output = {response: response}
    } catch (err) {
        if (!!err)
            output = {error: err.message}
        else
            output = {error: err}
    }
    return output
}

function logoutSync(baseUrl="https://platform.here.com") {
    // GET "https://platform.here.com/api/portal/clearAccessToken"
    // POST "https://account.here.com/clearCookies" "{}"
    // GET "https://account.here.com/api/account/sign-out" // optional
    let output = {}
    let response = {}
    let error = {}

    let token = ""
    try {
        let resp = makeRequestSync("GET", "https://platform.here.com/api/portal/accessToken", null, null)
        token = JSON.parse(resp).accessToken
    } catch (err) {
        error = Object.assign(error, {0: err.message})
    }

    try {
        let resp = makeRequestSync("GET", "https://platform.here.com/api/portal/clearAccessToken", null, null) ;
        response = Object.assign(response, {1: resp})
    } catch (err) {
        error = Object.assign(error, {1: err.message})
    }

    try {
        let resp = makeRequestSync("POST", "https://account.here.com/clearCookies", "{}", token) ;
        response = Object.assign(response, {2: resp})
    } catch (err) {
        error = Object.assign(error, {2: err.message})
    }

    output = {response: response, error: error}
    return output
}
