<?php
// ============================================
// НАСТРОЙКИ (замените на свои)
// ============================================
$confirmation_code = 'e3f55c4d';  // Ваш код подтверждения из VK
$access_token = 'vk1.a.EqaeP08Qq7AXX-An1o6UaMThR0_Rixz_ycXzJ9rRw28BHuWjTJJa_wxaOBZGRlazgcFbKw81J_FgiH5PW1Q_QmkG5De9HwUvVLBIG5Mj7veX-TpH57C_k-l2BaE1ebCbixF-iqYtg1A3-Pqcedorz0_RACtEshxdE1OZ13UD519OnwwBRiRRu_osswqhPcDqKQTUmgIbB0c0SBOeuWL-nQ';  // Токен сообщества VK
$group_id = '236802713';  // ID сообщества (число)

// Получаем данные от VK
$data = json_decode(file_get_contents('php://input'), true);

// Проверяем, что данные пришли
if (!$data) {
    http_response_code(400);
    echo 'Bad Request';
    exit;
}

// Обработка разных типов событий
switch ($data['type']) {
    case 'confirmation':
        // Подтверждение сервера
        echo $confirmation_code;
        exit;
        
    case 'message_new':
        // Новое сообщение от пользователя
        $user_id = $data['object']['message']['from_id'];
        $message_text = trim($data['object']['message']['text']);
        
        // Обрабатываем сообщение
        $answer = handleMessage($message_text, $user_id);
        
        // Отправляем ответ
        sendMessage($user_id, $answer);
        
        echo 'ok';
        exit;
        
    default:
        echo 'ok';
        exit;
}

// ============================================
// ФУНКЦИИ БОТА
// ============================================

/**
 * Обработка сообщения от пользователя
 */
function handleMessage($message, $user_id) {
    $message_lower = mb_strtolower($message, 'UTF-8');
    
    // Команда: начало/приветствие
    if ($message_lower == 'начать' || $message_lower == 'старт' || $message_lower == 'привет') {
        return "👋 Здравствуйте! Я бот детской поликлиники Тихорецка.\n\nЯ помогу:\n• Записать ребёнка к врачу\n• Узнать расписание\n• Получить контакты поликлиники\n\nЧто вас интересует?";
    }
    
    // Команда: запись к врачу
    if (strpos($message_lower, 'запись') !== false || strpos($message_lower, 'записаться') !== false) {
        return "📝 Для записи к врачу укажите:\n\n1. ФИО ребёнка\n2. Дата рождения\n3. Врач (педиатр, ЛОР, окулист, невролог)\n4. Удобное время\n\nПример:\nИванов Иван Иванович, 15.05.2020, педиатр, вторник 10:00";
    }
    
    // Команда: врачи
    if (strpos($message_lower, 'врач') !== false) {
        return "👨‍⚕️ В детской поликлинике Тихорецка работают:\n\n• Педиатр — ежедневно 8:00-18:00\n• ЛОР (отоларинголог) — пн, ср, пт\n• Окулист — вт, чт\n• Невролог — ср, пт\n• Хирург — чт\n\nДля записи напишите \"запись\"";
    }
    
    // Команда: контакты
    if (strpos($message_lower, 'контакт') !== false || strpos($message_lower, 'адрес') !== false) {
        return "📍 Детская поликлиника Тихорецка\n\nАдрес: ул. Красноармейская, 45\n📞 Телефон регистратуры: 8 (86146) 7-12-34\n🕐 Режим работы: пн-пт 8:00-18:00, сб 9:00-14:00\n\nЧасы работы: 8:00–18:00";
    }
    
    // Команда: помощь
    if ($message_lower == 'помощь' || $message_lower == 'help') {
        return "🤖 Команды бота:\n\n• Начать — начать диалог\n• Запись — записаться к врачу\n• Врачи — список врачей\n• Контакты — адрес и телефон\n• Помощь — это сообщение";
    }
    
    // Если ничего не подошло
    return "❓ Я не понял запрос.\n\nНапишите \"помощь\", чтобы увидеть список команд.";
}

/**
 * Отправка сообщения пользователю
 */
function sendMessage($user_id, $message) {
    global $access_token;
    
    $url = 'https://api.vk.com/method/messages.send';
    $params = [
        'user_id' => $user_id,
        'message' => $message,
        'random_id' => rand(1, 999999),
        'access_token' => $access_token,
        'v' => '5.131'
    ];
    
    $response = file_get_contents($url . '?' . http_build_query($params));
    return $response;
}

?>