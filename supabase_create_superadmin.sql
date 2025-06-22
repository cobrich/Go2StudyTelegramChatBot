-- SQL скрипт для создания суперадмина в Supabase
-- Выполните этот скрипт в Supabase Dashboard → SQL Editor

-- Создание суперадмина
INSERT INTO admins (
    user_id, 
    username, 
    full_name, 
    is_super_admin, 
    created_by, 
    created_at, 
    updated_at
) VALUES (
    1354242060,                              -- ваш Telegram user_id
    'Bekzat_Erikuly',                        -- ваш username
    'Tursun Bekzat Yerikuly',               -- ваше полное имя
    true,                                    -- суперадмин
    NULL,                                    -- создан системой
    CURRENT_TIMESTAMP,                       -- время создания
    CURRENT_TIMESTAMP                        -- время обновления
) ON CONFLICT (user_id) DO UPDATE SET
    username = EXCLUDED.username,
    full_name = EXCLUDED.full_name,
    is_super_admin = EXCLUDED.is_super_admin,
    updated_at = CURRENT_TIMESTAMP;

-- Проверяем, что суперадмин создан
SELECT 
    user_id,
    username,
    full_name,
    is_super_admin,
    created_at
FROM admins 
WHERE user_id = 1354242060;

-- Проверяем общее количество админов
SELECT 
    COUNT(*) as total_admins,
    COUNT(*) FILTER (WHERE is_super_admin = true) as super_admins,
    COUNT(*) FILTER (WHERE is_super_admin = false) as regular_admins
FROM admins; 