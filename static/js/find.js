const socket = io()

const difficult = window.location.href.split("/").pop()
socket.emit("join", difficult.charAt(0).toUpperCase())

socket.on("response", function (number) {
    window.location.href = window.location.href.replace(
        "find/" + difficult, "battle/" + number.toString())
})