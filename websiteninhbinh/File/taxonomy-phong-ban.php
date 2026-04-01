<?php get_header(); ?>
<div id="main-body">
	<div class="container">
		<div class="main-body">
			<div class="line-block"></div>
			<div class="row">
				<!--Sidebar Left-->
				<!--END Sidebar Left-->

				<div class="col-xs-12 col-md-9">
					<div id="main-content" class="main-content main-content-6">
						<div class="single">
							<div class="block-title s-title">
								<h3><i class="fa fa-address-card ico-title"></i> <a href="#">THÔNG TIN - <?php single_cat_title(); ?></a></h3>
							</div>
							<div class="line"></div>
							<div class="s-content">
								<div class="single-content parts-content" style="padding-bottom: 0;">
									<?php
									$term_slug = get_queried_object()->slug;
									$_dataNew = array();
									$_data = getData($term_slug);
									foreach ($_data as $key => $value) {
										array_push($_dataNew, $value->post_id);
									}
									$term_slug = get_queried_object()->slug;
$args = array ( 
    'post_type' => 'co-cau-to-chuc',
    'post_status' => 'publish',
    'tax_query' => array(
        array(
            'taxonomy' => 'phong-ban',
            'field' => 'slug',
            'terms' => $term_slug
        )
    ),
    'meta_key' => 'wpcf-cctc-thu-tu', 
    'post__in'=> $_dataNew,           
    'orderby' => 'meta_value_num',   
    'order'   => 'ASC',               
    'posts_per_page' => 100,
    'paged' => $paged,
									);
								?>
								<?php $wp_query = new WP_query($args); ?>
								<div class="thongtin-phongban">
									<?php
										$page = get_page_by_path( $term_slug );
										//print_r($page);
									?>
									<?php echo apply_filters('the_content', $page->post_content); ?>
								</div>
								<?php if ($wp_query->have_posts()) : ?>
									<?php while ($wp_query->have_posts()) : $wp_query->the_post(); ?>
									<div class="thongtin-canbo">
										<div class="col-xs-12 col-sm-3 col-md-3">
											<div class="thongtin-canbo-img">
												<?php if(ddev_check_link_thumb($post->ID) == "") : ?>
													<img src="<?php echo get_template_directory_uri(); ?>/images/avatar.png" />
												<?php else: ?>
													<?php ddev_thumb(220, null); ?>
												<?php endif; ?>
											</div>
										</div>
										<div class="col-xs-12 col-sm-9 col-md-9">
											<ul class="thongtin-canbo-caption">
												<li class="text-primary hoten"><?php the_title(); ?></li>
												<li><label>Phòng ban:</label><?php echo get_queried_object()->name; ?></li>
												<li><label>Chức vụ:</label><?php echo types_render_field('cctc-chuc-vu', array('output' => 'raw')); ?></li>
												<li><label>Điện thoại:</label><?php echo types_render_field('cctc-dien-thoai', array('output' => 'raw')); ?></li>
												<li><label>Email:</label><?php echo types_render_field('cctc-email', array('output' => 'raw')); ?></li>
												<li><label>Thông tin thêm:</label><?php echo types_render_field('cctc-thong-tin-them', array('output' => 'raw')); ?></li>
											</ul>
										</div>
									</div>
									<?php endwhile; ?>
								<?php endif; ?>

								</div>
							</div><!--End .s-content-->
						</div><!--End .single-->
					</div><!--End .main-content-->
					<div class="related">
						<div class="related-title">
							<h3><i class="fa fa-list-ul"></i> Các phòng ban khác</h3>
							<?php 
								$terms = get_terms( array(
								    'taxonomy' => 'phong-ban',
								    'hide_empty' => false,
								    ''
								) );?>
								<ul class="list-group list-phongban">
									<?php 
									foreach ($terms as $key => $term) {
										if($term->slug != $term_slug) { ?>
										<li>
											<i class="fa fa-caret-right"></i>
											<a href="/phong-ban/<?php echo $term->slug; ?>">
												<?php echo $term->name; ?>
											</a>
										</li>
									<?php 
										}
									}
								?>
								</ul>
						</div>
					</div>
				</div>

				<!--Sidebar Right-->
				<?php get_sidebar('right'); ?>
				<!--END Sidebar Right-->
			</div>
		</div>
	</div>
</div>
<?php get_footer(); ?>