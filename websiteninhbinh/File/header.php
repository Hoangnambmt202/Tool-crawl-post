<!DOCTYPE html>
<html lang="vi">

<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?php ddev_seotitles(); ?></title>
    <meta name="description" content="<?php bloginfo('description'); ?>" />
    <meta name="keywords" content="<?php bloginfo('description'); ?>" />

    <?php
    if (!function_exists('get_first_image_from_content')) {
        function get_first_image_from_content($content)
        {
            if (empty($content)) return '';

            // Ảnh thông thường
            if (preg_match('/<img[^>]+src\s*=\s*["\']([^"\']+)["\'][^>]*>/i', $content, $m)) return $m[1];
            if (preg_match('/<img[^>]+src\s*=\s*([^\s>]+)[^>]*>/i', $content, $m)) return trim($m[1], '"\'');

            // Lazy-load (data-src)
            if (preg_match('/<img[^>]+data-src\s*=\s*["\']([^"\']+)["\'][^>]*>/i', $content, $m)) return $m[1];

            // Gallery shortcode
            if (preg_match('/\[gallery[^\]]*ids\s*=\s*["\']?([0-9,]+)["\']?[^\]]*\]/i', $content, $m)) {
                $ids = explode(',', $m[1]);
                if (!empty($ids[0])) {
                    $img_data = wp_get_attachment_image_src((int)$ids[0], 'full');
                    if (!empty($img_data[0])) return $img_data[0];
                }
            }

            // Figure block
            if (preg_match('/<figure[^>]*>.*?<img[^>]+src\s*=\s*["\']([^"\']+)["\'][^>]*>.*?<\/figure>/is', $content, $m)) return $m[1];

            return '';
        }
    }

    if (!function_exists('normalize_image_url')) {
        function normalize_image_url($img_url)
        {
            if (empty($img_url)) return '';

            if (strpos($img_url, 'http') === false) {
                $img_url = (strpos($img_url, '//') === 0)
                    ? 'https:' . $img_url
                    : rtrim(get_site_url(), '/') . '/' . ltrim($img_url, '/');
            }

            // Ép HTTPS để Facebook/Zalo không bị block
            $img_url = str_replace('http://', 'https://', $img_url);

            // Bỏ query string (tránh cache-bust làm sai URL)
            return strtok($img_url, '?');
        }
    }

    if (!function_exists('get_image_mime_type')) {
        function get_image_mime_type($url)
        {
            $ext = strtolower(pathinfo(strtok($url, '?'), PATHINFO_EXTENSION));
            $map = [
                'jpg'  => 'image/jpeg',
                'jpeg' => 'image/jpeg',
                'png'  => 'image/png',
                'gif'  => 'image/gif',
                'webp' => 'image/webp',
            ];
            return $map[$ext] ?? 'image/jpeg';
        }
    }

    // ============================================================
    // 2. BIẾN DÙNG CHUNG
    // ============================================================

    // Cache các setting để tránh gọi lặp
    $ddev_banner_url        = function_exists('ddev_get_setting') ? ddev_get_setting('ddev_banner_url') : '';
    $ddev_banner_mobile_url = function_exists('ddev_get_setting') ? ddev_get_setting('ddev_banner_mobile_url') : '';
    $ddev_color             = function_exists('ddev_get_setting') ? ddev_get_setting('ddev_color') : '';

    $current_og_url = 'https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
    $og_type        = 'website';
    $og_desc        = get_bloginfo('description');

    // Ảnh mặc định (banner trang web)
    $default_image = !empty($ddev_banner_url)
        ? $ddev_banner_url
        : get_template_directory_uri() . '/images/banner/banner.jpg';

    $img_src_fb = normalize_image_url($default_image);
    $img_width  = 1200;
    $img_height = 630;

    // ============================================================
    // 3. XỬ LÝ BÀI VIẾT / TRANG TĨNH
    // ============================================================

    if (is_single() || is_page()) {
        $og_type = 'article';
        global $post;
        $post_id_fb = $post->ID;
        $temp_img   = '';

        // Ưu tiên 1: Featured image (thumbnail)
        if (has_post_thumbnail($post_id_fb)) {
            $thumbnail_id  = get_post_thumbnail_id($post_id_fb);
            $img_array_fb  = wp_get_attachment_image_src($thumbnail_id, 'full');
            if (!empty($img_array_fb[0])) {
                $temp_img   = $img_array_fb[0];
                $img_width  = $img_array_fb[1];
                $img_height = $img_array_fb[2];
            }
        }

        // Ưu tiên 2: Ảnh đầu tiên trong nội dung
        if (empty($temp_img)) {
            $temp_img = get_first_image_from_content($post->post_content);
        }

        // Ưu tiên 3: Attachment đính kèm bài viết
        if (empty($temp_img)) {
            $attachments = get_posts([
                'post_type'      => 'attachment',
                'post_mime_type' => 'image',
                'post_parent'    => $post_id_fb,
                'posts_per_page' => 1,
                'orderby'        => 'menu_order',
                'order'          => 'ASC',
            ]);
            if (!empty($attachments)) {
                $img_data = wp_get_attachment_image_src($attachments[0]->ID, 'full');
                if (!empty($img_data[0])) {
                    $temp_img   = $img_data[0];
                    $img_width  = $img_data[1];
                    $img_height = $img_data[2];
                }
            }
        }

        if (!empty($temp_img)) {
            $img_src_fb = normalize_image_url($temp_img);
        }

        // Mô tả bài viết
        $excerpt_fb = strip_tags(get_the_excerpt());
        if (empty($excerpt_fb)) {
            $excerpt_fb = wp_trim_words(strip_tags($post->post_content), 30, '...');
        }
        if (!empty($excerpt_fb)) {
            $og_desc = $excerpt_fb;
        }
    }

    // SEO title
    ob_start();
    ddev_seotitles();
    $seo_title_clean = trim(strip_tags(ob_get_clean()));

    // MIME type thực của ảnh (không hardcode jpeg)
    $og_image_type = get_image_mime_type($img_src_fb);

    // Canonical URL
    $canonical_url = (is_single() || is_page()) ? get_permalink() : $current_og_url;

    // Color theme
    $color_file      = !empty($ddev_color) ? $ddev_color : 'color-default.css';
    $color_file_path = TEMPLATEPATH . '/css/color/' . $color_file;
    $main_color      = '#0d9fd0';
    if (file_exists($color_file_path)) {
        $css_content = file_get_contents($color_file_path);
        if (preg_match('/\.main-menu\s*\{\s*background\s*:\s*([^;]+);/', $css_content, $m)) {
            $main_color = trim($m[1]);
        }
    }
    ?>

    <!-- Open Graph / Facebook / Zalo -->
    <meta property="og:locale" content="vi_VN" />
    <meta property="og:type" content="<?php echo esc_attr($og_type); ?>" />
    <meta property="og:site_name" content="<?php echo esc_attr(get_bloginfo('name')); ?>" />
    <meta property="og:url" content="<?php echo esc_url($current_og_url); ?>" />
    <meta property="og:title" content="<?php echo esc_attr($seo_title_clean); ?>" />
    <meta property="og:description" content="<?php echo esc_attr($og_desc); ?>" />
    <meta property="og:image" content="<?php echo esc_url($img_src_fb); ?>" />
    <meta property="og:image:secure_url" content="<?php echo esc_url($img_src_fb); ?>" />
    <meta property="og:image:width" content="<?php echo esc_attr($img_width); ?>" />
    <meta property="og:image:height" content="<?php echo esc_attr($img_height); ?>" />
    <meta property="og:image:type" content="<?php echo esc_attr($og_image_type); ?>" />
    <meta property="og:image:alt" content="<?php echo esc_attr($seo_title_clean); ?>" />

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="<?php echo esc_attr($seo_title_clean); ?>" />
    <meta name="twitter:description" content="<?php echo esc_attr($og_desc); ?>" />
    <meta name="twitter:image" content="<?php echo esc_url($img_src_fb); ?>" />
    <meta name="twitter:image:alt" content="<?php echo esc_attr($seo_title_clean); ?>" />

    <link rel="canonical" href="<?php echo esc_url($canonical_url); ?>" />
    <link rel="preload" href="<?php echo esc_url($img_src_fb); ?>" as="image" />
    <link rel="shortcut icon" href="<?php echo get_template_directory_uri(); ?>/ico.png" />

    <!-- Stylesheets -->
    <link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/libs/font-awesome/css/font-awesome.min.css" />
    <link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/libs/bootstrap/css/bootstrap.min.css" />
    <link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/css/jquery.mCustomScrollbar.min.css" />
    <link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/css/prettyPhoto.css" />
    <link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/css/style.css" />
    <link rel="stylesheet" href="<?php echo get_template_directory_uri(); ?>/css/color/<?php echo esc_attr($color_file); ?>" />

    <style>
        .header-banner .banner {
            background-color: <?php echo $main_color; ?> !important;
        }
    </style>
</head>

<body>
    <div id="fb-root"></div>
    <!-- Facebook SDK (async, version mới nhất) -->
    <script>
        (function(d, s, id) {
            var js, fjs = d.getElementsByTagName(s)[0];
            if (d.getElementById(id)) return;
            js = d.createElement(s);
            js.id = id;
            js.async = true;
            js.src = "https://connect.facebook.net/vi_VN/sdk.js#xfbml=1&version=v21.0";
            fjs.parentNode.insertBefore(js, fjs);
        }(document, 'script', 'facebook-jssdk'));
    </script>

    <div id="wrapper">
        <header id="header">
            <div class="header-banner">
                <div class="container">
                    <div class="row">
                        <div class="col-xs-12 col-md-12">
                            <a href="<?php echo esc_url(home_url('/')); ?>">
                                <div class="row text-center banner">
                                    <?php
                                    $site_name = get_bloginfo('name');
                                    if (wp_is_mobile()) :
                                        $mobile_src = !empty($ddev_banner_mobile_url)
                                            ? $ddev_banner_mobile_url
                                            : get_template_directory_uri() . '/images/banner/banner_mobile.jpg';
                                    ?>
                                        <img width="100%" src="<?php echo esc_url($mobile_src); ?>" alt="<?php echo esc_attr($site_name); ?>" loading="lazy" />
                                        <?php else :
                                        if (!empty($ddev_banner_url)) :
                                            $ext = strtoupper(pathinfo($ddev_banner_url, PATHINFO_EXTENSION));
                                            if ($ext === 'SWF') : ?>
                                                <!-- Flash (SWF) không còn được hỗ trợ — hãy thay bằng ảnh hoặc video -->
                                                <p style="color:red;">Banner SWF không được hỗ trợ. Vui lòng cập nhật banner dạng JPG/PNG/MP4.</p>
                                            <?php else : ?>
                                                <img width="100%" src="<?php echo esc_url($ddev_banner_url); ?>" alt="<?php echo esc_attr($site_name); ?>" loading="lazy" />
                                            <?php endif; ?>
                                        <?php else : ?>
                                            <img width="100%" src="<?php echo get_template_directory_uri(); ?>/images/banner/banner.jpg" alt="<?php echo esc_attr($site_name); ?>" loading="lazy" />
                                        <?php endif; ?>
                                    <?php endif; ?>
                                </div>
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="main-menu">
                <div class="container">
                    <div class="row">
                        <div class="col-xs-12 col-md-12">
                            <nav class="row navbar navbar-default main-navbar" role="navigation">
                                <div class="navbar-header">
                                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#bs-navbar-collapse">
                                        <span class="sr-only">Toggle navigation</span>
                                        <span class="icon-bar"></span>
                                        <span class="icon-bar"></span>
                                        <span class="icon-bar"></span>
                                    </button>
                                    <a class="hidden-sm navbar-brand" href="<?php echo esc_url(home_url('/')); ?>">
                                        <i class="fa fa-home" aria-hidden="true"></i>
                                    </a>
                                </div>
                                <div class="collapse navbar-collapse" id="bs-navbar-collapse">
                                    <?php wp_nav_menu([
                                        'theme_location' => 'main_nav',
                                        'container'      => 'false',
                                        'menu_id'        => 'main-nav',
                                        'menu_class'     => 'nav navbar-nav main-nav',
                                        'fallback_cb'    => 'wp_bootstrap_navwalker::fallback',
                                        'walker'         => new wp_bootstrap_navwalker(),
                                    ]); ?>
                                </div>
                            </nav>
                        </div>
                    </div>
                </div>
            </div>

            <div class="header-tool">
                <div class="container">
                    <div class="row">
                        <div class="col-xs-12 col-md-2">
                            <div class="ht-block timezone">
                                <?php ddev_date('vi'); ?>
                            </div>
                        </div>
                        <div class="hidden-xs hidden-sm col-xs-12 col-md-7">
                            <div class="ht-block welcome">
                                <!-- Thay <marquee> (đã lỗi thời) bằng CSS animation -->
                                <div class="marquee-wrapper" style="overflow:hidden;white-space:nowrap;">
                                    <span class="marquee-text" style="display:inline-block;animation:marquee 20s linear infinite;">
                                        <?php echo ddev_get_option('ddev_welcome'); ?>
                                    </span>
                                </div>
                                <style>
                                    @keyframes marquee {
                                        from {
                                            transform: translateX(100%);
                                        }

                                        to {
                                            transform: translateX(-100%);
                                        }
                                    }

                                    .marquee-wrapper:hover .marquee-text {
                                        animation-play-state: paused;
                                    }
                                </style>
                            </div>
                        </div>
                        <div class="col-xs-12 col-md-3">
                            <div class="search">
                                <form class="searchform" method="get" action="<?php bloginfo('url'); ?>/">
                                    <div class="input-group">
                                        <input type="hidden" name="post_type[]" value="post">
                                        <input type="hidden" name="post_type[]" value="van-ban">
                                        <input type="hidden" name="post_type[]" value="thu-tuc-hanh-chinh">
                                        <input type="hidden" name="post_type[]" value="tai-nguyen">
                                        <input type="text" class="form-control" placeholder="Tìm kiếm.." value="<?php the_search_query(); ?>" name="s">
                                        <span class="input-group-btn">
                                            <button class="btn btn-search" type="submit"><i class="fa fa-search"></i></button>
                                        </span>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </header>