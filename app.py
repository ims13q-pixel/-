-- blockspin_final.lua
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local player = Players.LocalPlayer

local WEBHOOK = "https://YOUR-VERCEL-URL.vercel.app/api/report"
local requestFunc = request or http_request or (syn and syn.request) or (krnl and krnl.request)

-- ربط أسماء المهارات بأيقونات FontAwesome
local icons = {
    ["fishing"] = "fa-fish",
    ["stamina"] = "fa-bolt",
    ["shelf stocker"] = "fa-box",
    ["janitor"] = "fa-broom",
    ["swiper"] = "fa-credit-card",
    ["farming"] = "fa-seedling",
    ["cook"] = "fa-fire",
    ["total level"] = "fa-star"
}

local function getIcon(skillName)
    local lower = skillName:lower()
    for k, v in pairs(icons) do
        if lower:find(k) then return v end
    end
    return "fa-gamepad" -- أيقونة افتراضية لأي مهارة ثانية
end

local function sendReport()
    local statsData = {
        name = player.Name,
        cash = 0,
        bank = 0,
        total_level = 0,
        skills = {}
    }

    local gui = player:FindFirstChild("PlayerGui")
    if gui then
        for _, obj in ipairs(gui:GetDescendants()) do
            if obj:IsA("TextLabel") or obj:IsA("TextButton") then
                local text = obj.Text
                
                -- الفلوس
                local bankMatch = text:match("Bank Balance:%s*%$(%d+)")
                if bankMatch then statsData.bank = tonumber(bankMatch) end
                
                local handMatch = text:match("Hand Balance:%s*%$(%d+)")
                if handMatch then statsData.cash = tonumber(handMatch) end

                -- اللفل الكلي
                local totalLvlMatch = text:match("Total Level:%s*(%d+)") or text:match("LevelText")
                if totalLvlMatch and tonumber(totalLvlMatch) then
                    statsData.total_level = tonumber(totalLvlMatch)
                end

                -- المهارات
                local skillName, skillLevel = text:match("([%a%s]+):%s*(%d+)")
                if skillName and skillLevel then
                    skillName = skillName:gsub("^%s+", ""):gsub("%s+$", "")
                    if skillName ~= "Total Level" and skillName ~= "Character Level" and #skillName > 2 then
                        statsData.skills[skillName] = tonumber(skillLevel)
                    end
                end
            end
        end
    end

    -- إضافة الأيقونة لكل مهارة
    local skillsWithIcons = {}
    for name, lvl in pairs(statsData.skills) do
        table.insert(skillsWithIcons, { name = name, level = lvl, icon = getIcon(name) })
    end
    statsData.skills = skillsWithIcons

    -- الإرسال
    pcall(function()
        requestFunc({
            Url = WEBHOOK,
            Method = "POST",
            Headers = { ["Content-Type"] = "application/json" },
            Body = HttpService:JSONEncode(statsData)
        })
    end)
end

task.spawn(sendReport)
task.spawn(function()
    while task.wait(15) do
        sendReport()
    end
end)

print("[*] Final Hook Started for " .. player.Name)
