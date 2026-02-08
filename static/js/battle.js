const sidebar = document.querySelectorAll(".sidebar span")
const image = document.getElementById("image")
const tasks = document.tasks
const userId = document.userId
let resolve = document.resolve

const socket = io()


function update() {
    for (let i = 0; i < sidebar.length; i++) {
        if (resolve[i] === userId) sidebar[i].classList.add("win")
        else if (resolve[i] === 0) {
            document.getElementById("title").innerText = tasks[i]["title"]
            document.getElementById("condition").innerHTML = tasks[i]["condition"]
            document.querySelectorAll(".main > p > img").forEach(function (img) {
                img.onload = function () {
                    let vertical = parseFloat(img.style.verticalAlign) * 1.6
                    let height = parseFloat(window.getComputedStyle(img).height) * 1.7
                    img.style.verticalAlign = vertical.toString() + "pt"
                    img.style.height = height.toString() + "px" }})
            if (tasks[i]["image"] == null) image.classList.add("d-none")
            else {
                if (tasks[i]["image"].startsWith("condition/")) image.src = "/static/" + tasks[i]["image"]
                else if (tasks[i]["image"].startsWith("https://")) image.src = tasks[i]["image"]
                image.classList.remove("d-none")
            }
            sidebar[i].classList.add("current")
            break
        } else sidebar[i].classList.add("loose")
    }
}

window.onload = function () {
    update()
    socket.emit("start")
}

function check() {
    let answer = document.querySelector("input[name=answer]").value
    if (answer !== "") socket.emit("check", [document.number, answer])
}

socket.on("invalid", function () {
    document.querySelector("input[name=answer]").classList.add("invalid")})

document.querySelector("input[name=answer]").oninput = function () {
    document.querySelector("input[name=answer]").classList.remove("invalid")}

socket.on("correct", function (data) {
    resolve = data[0]; update()
    document.querySelector("input[name=answer]").value = ""
    alert("Поздравляем, вы правильно решили задачу. Ваш счёт: " + data[1] + " !")
    if (!resolve.includes(0)) finish(data[1])
})

socket.on("loose", function (data) {
    resolve = data[0]; update()
    document.querySelector("input[name=answer]").value = ""
    document.querySelector("input[name=answer]").classList.remove("invalid")
    alert("Соперник решил задачу быстрее. Ваш счёт: " + data[1] + " !")
    if (!resolve.includes(0)) finish(data[1])
})

function finish(score) {
    let nums = score.split(" : ")
    let a = parseInt(nums[0])
    let b = parseInt(nums[1])
    if (a > b) {
        document.getElementById("title").innerText = "Победа [ " + score + " ] !"
        document.getElementById("condition").innerHTML = "Поздравляем, вы победили в этом турнире!<br>Ваш рейтинг будет повышен по формуле Elo."
    } else if (a < b) {
        document.getElementById("title").innerText = "Поражение [ " + score + " ] !"
        document.getElementById("condition").innerHTML = "К сожалению, вы проиграли в этом турнире : (<br>Ваш рейтинг понизится по формуле Elo."
    } else {
        document.getElementById("title").innerText = "Ничья [ " + score + " ] !"
        document.getElementById("condition").innerHTML = "В этом турнире победила дружба, однако<br>рейтинг всё равно изменится по формуле Elo."
    }
    image.classList.add("d-none")
    document.querySelector(".form").classList.add("d-none")
    document.querySelector(".finish").classList.remove("d-none")
}