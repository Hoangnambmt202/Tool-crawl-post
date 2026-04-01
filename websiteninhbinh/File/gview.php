<?php
/********************************************************************
// Google View Document - Optimized Version
// - Mobile: Direct PDF viewing for better compatibility
// - Desktop: Google Viewer for PDF (no sidebar)
// - HTTPS enforcement for security
// - Modern download button
********************************************************************/

/**
 * Auto-insert [gview] shortcode when adding files from Media Library
 */
function ddev_media_insert($html, $id, $attachment) {
    $gdoc_url = '';
    
    if (isset($attachment['url'])) {
        $gdoc_url = $attachment['url'];
    } elseif ($id > 0) {
        $post = get_post($id);
        if ($post) {
            $gdoc_url = wp_get_attachment_url($id);
        }
    }
    
    $filetype = wp_check_filetype($gdoc_url);
    $filetype_ext = strtoupper($filetype['ext']);
    
    // Only create shortcode for viewable files (exclude archives and images)
    if (
        $gdoc_url != '' &&
        !in_array($filetype_ext, ['RAR', 'ZIP', 'JPG', 'JPEG', 'PNG', 'GIF', 'BMP'])
    ) {
        return '[gview file="' . esc_url($gdoc_url) . '"]';
    } else {
        return $html;
    }
}
add_filter('media_send_to_editor', 'ddev_media_insert', 20, 3);


/**
 * Display documents with appropriate viewer
 */
function create_gview_shortcode($args, $content) {
    // Validation
    if (empty($args['file'])) {
        return '<p style="color:red;font-weight:bold;">❌ Lỗi: Không tìm thấy tệp cần hiển thị.</p>';
    }
    
    $file = $args['file'];
    
    // 🔒 Force HTTPS to prevent Mixed Content errors
    if (strpos($file, 'http://') === 0) {
        $file = str_replace('http://', 'https://', $file);
    }
    
    $file_esc = esc_url($file);
    $is_mobile = wp_is_mobile();
    $height = $is_mobile ? '500' : '800';
    
    $file_lower = strtolower($file);
    $encoded_file = urlencode($file); // Cần thiết cho MS Office và Google Viewer

    // Handle MP4 videos
    if (strpos($file_lower, 'mp4') !== false) {
        $content = '<video width="100%" controls style="max-width:100%;border:1px solid #ddd;border-radius:8px;">
                        <source src="' . $file_esc . '" type="video/mp4">
                        Trình duyệt của bạn không hỗ trợ video HTML5.
                    </video>';
    }
    
    // Handle PDF files
    elseif (strpos($file_lower, 'pdf') !== false) {
        if ($is_mobile) {
            // Mobile: Direct PDF viewing for better compatibility
            $content = '<iframe 
                            id="pdf-viewer" 
                            src="' . $file_esc . '" 
                            width="100%" 
                            height="' . $height . '" 
                            frameborder="0" 
                            style="border:1px solid #ddd;border-radius:8px;">
                            <p>Trình duyệt không hỗ trợ iframe. <a href="' . $file_esc . '">Tải file tại đây</a></p>
                        </iframe>';
        } else {
            // Desktop: Use Google Viewer to eliminate sidebar thumbnails
            $content = '<iframe 
                            id="pdf-viewer" 
                            src="https://docs.google.com/gview?url=' . $encoded_file . '&embedded=true" 
                            width="100%" 
                            height="' . $height . '" 
                            frameborder="0" 
                            style="border:1px solid #ddd;border-radius:8px;">
                            <p>Đang tải PDF... <a href="' . $file_esc . '">Tải file tại đây</a></p>
                        </iframe>';
        }
    }
    
    // Handle Office files (doc, xls, ppt, etc.)
    else {
        if ($is_mobile) {
            // Mobile: Mặc định dùng Google Docs Viewer cho các file Office. 
            // Trình duyệt di động (đặc biệt là iOS WebView/Safari) thường chặn 3rd-party cookie, làm MS Viewer bị trắng trang.
            $content = '<iframe 
                            id="office-viewer" 
                            src="https://docs.google.com/gview?url=' . $encoded_file . '&embedded=true" 
                            width="100%" 
                            height="' . $height . '" 
                            frameborder="0" 
                            style="border:1px solid #ddd;border-radius:8px;">
                            <p>Đang tải file... Nếu không hiển thị, <a href="' . $file_esc . '">nhấn vào đây để tải về</a></p>
                        </iframe>';
        } else {
            // Desktop: Dùng MS Office Apps Live viewer
            // Sử dụng /op/embed.aspx thay vì view.aspx để chuẩn iframe hơn.
            $content = '<iframe 
                            id="office-viewer" 
                            src="https://view.officeapps.live.com/op/embed.aspx?src=' . $encoded_file . '" 
                            width="100%" 
                            height="' . $height . '" 
                            frameborder="0" 
                            style="border:1px solid #ddd;border-radius:8px;">
                            <p>Đang tải file... Nếu không hiển thị, <a href="' . $file_esc . '">nhấn vào đây để tải về</a></p>
                        </iframe>';
        }
    }
    
    // Add download button
    $content .= '<div style="text-align:center;margin-top:20px;margin-bottom:10px;">
                    <a href="' . $file_esc . '" 
                       download 
                       target="_blank"
                       rel="noopener"
                       class="btn-download-file"
                       style="display:inline-block;
                              background:#28a745;
                              color:#ffffff;
                              padding:12px 30px;
                              border-radius:5px;
                              text-decoration:none;
                              font-weight:600;
                              font-size:14px;
                              box-shadow:0 2px 8px rgba(40,167,69,0.3);
                              transition:all 0.3s ease;
                              border:none;">
                        <i class="fa fa-download" style="margin-right:6px;"></i>Tải xuống
                    </a>
                 </div>';
    
    return $content;
}
add_shortcode('gview', 'create_gview_shortcode');

?>