<?php
/**
 * The admin-specific functionality of the plugin.
 *
 * @link  https://www.getshifter.io
 * @since 1.0.0
 *
 * @package    Shifter
 * @subpackage Shifter/admin
 */

/**
 * The admin-specific functionality of the plugin.
 *
 * Defines the plugin name, version, and two examples hooks for how to
 * enqueue the admin-specific stylesheet and JavaScript.
 *
 * @package    Shifter
 * @subpackage Shifter/admin
 * @author     DigitalCube <hello@getshifter.io>
 */
class Shifter_Admin {


	/**
	 * The ID of this plugin.
	 *
	 * @since  1.0.0
	 * @access private
	 * @var    string    $plugin_name    The ID of this plugin.
	 */
	private $plugin_name;

	/**
	 * The version of this plugin.
	 *
	 * @since  1.0.0
	 * @access private
	 * @var    string    $version    The current version of this plugin.
	 */
	private $version;

	/**
	 * Initialize the class and set its properties.
	 *
	 * @since 1.0.0
	 * @param string $plugin_name The name of this plugin.
	 * @param string $version     The version of this plugin.
	 */
	public function __construct( $plugin_name, $version ) {

		$this->plugin_name = $plugin_name;
		$this->version     = $version;

	}

	/**
	 * Register the stylesheets for the admin area.
	 *
	 * @since 1.0.0
	 */
	public function enqueue_styles() {

		/**
		 * This function is provided for demonstration purposes only.
		 *
		 * An instance of this class should be passed to the run() function
		 * defined in Shifter_Loader as all of the hooks are defined
		 * in that particular class.
		 *
		 * The Shifter_Loader will then create the relationship
		 * between the defined hooks and the functions defined in this
		 * class.
		 */

		wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'css/shifter-admin.css', array(), $this->version, 'all' );

	}

	/**
	 * Register the JavaScript for the admin area.
	 *
	 * @since 1.0.0
	 */
	public function enqueue_scripts() {

		/**
		 * This function is provided for demonstration purposes only.
		 *
		 * An instance of this class should be passed to the run() function
		 * defined in Shifter_Loader as all of the hooks are defined
		 * in that particular class.
		 *
		 * The Shifter_Loader will then create the relationship
		 * between the defined hooks and the functions defined in this
		 * class.
		 */

		wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'js/shifter-admin.js', array( 'jquery' ), $this->version, false );

	}

	/**
	 * Display Container Time
	 *
	 * @since 1.0.0
	 */
	public function notice_shifter_dashboard_timer() {
		$bootup_filename = '../.bootup';
		$hard_limit      = 180;
		if ( file_exists( $bootup_filename ) ) {
			$unixtime       = file_get_contents( $bootup_filename, true );
			$shifter_remain = $hard_limit - round( ( time() - intval( $unixtime ) ) / 60 );
			if ( $shifter_remain < 3 ) {
				?>
	<div class="error"><ul>
	Notice: Shifter will power down WordPress in few minutes. Please restart your from the Shifter Dashboard.
	</ul></div>
				<?php
			} elseif ( $shifter_remain < 30 ) {
				?>
	<div class="error"><ul>
	Notice: Shifter will power down WordPress in <?php echo $shifter_remain; ?> minutes. Please restart your from the Shifter Dashboard.
	</ul></div>
				<?php
			}
		}
	}

	/**
	 * Fix for Yoast Sitemaps
	 *
	 * @since 1.0.0
	 */
	public function yoast_sitemaps_fix() {
		if ( ! function_exists( 'surbma_yoast_seo_sitemap_to_robotstxt_init' ) ) {
			add_filter(
				'robots_txt',
				function ( $output ) {
					$options = get_option( 'wpseo_xml' );

					if ( class_exists( 'WPSEO_Sitemaps' ) && true === $options['enablexmlsitemap'] ) {
						$home_url = get_home_url();
						$output  .= "Sitemap: {$home_url}/sitemap_index.xml\n";
					}

					return $output;
				},
				9999,
				1
			);
		}
	}

	/**
	 * Redis Cache Fix
	 *
	 * @since 1.0.0
	 */
	public function option_cache_flush( $option, $old_value = '', $value = '' ) {
		if ( ! empty( $option ) ) {
			wp_cache_delete( $option, 'options' );
			foreach ( array( 'alloptions', 'notoptions' ) as $options_name ) {
				 $options = wp_cache_get( $options_name, 'options' );
				if ( ! is_array( $options ) ) {
					$options = array();
				}
				if ( isset( $options[ $option ] ) ) {
					unset( $options[ $option ] );
					wp_cache_set( $options_name, $options, 'options' );
				}
				 unset( $options );
			}
		}
		return;
	}


	/**
	 * Shifter Heartbeat
	 *
	 * @since 1.0.0
	 */
	public function shifter_heartbert_on_sitepreview_writeScript() {
		if ( is_user_logged_in() ) {
			?>
		<script>
		function shifter_heartbert_getajax() {
			var xhr= new XMLHttpRequest();
			xhr.open("GET","/wp-admin/admin-ajax.php?action=nopriv_heartbeat");
			xhr.send();
		}
		setInterval("shifter_heartbert_getajax()", 30000);
		</script>
			<?php
		}
	}


	/**
	 * Shifter Mail From Helper
	 *
	 * @since 1.0.0
	 */
	public function shifter_mail_from( $email_address ) {
		return 'wordpress@app.getshifter.io';
	}

	/**
	 * Integrations between Shifter and Algolia
	 *
	 * @since 1.0.0
	 */
	public function shifter_replace_algolia_permalink( $shared_attributes, $post ) {
		$replaced_domain = getenv( 'SHIFTER_DOMAIN' );
		if ( ! $replaced_domain ) {
			$replaced_domain = getenv( 'CF_DOMAIN' );
		}
		if ( $replaced_domain ) {
			$url            = $shared_attributes['permalink'];
			$parsed_url     = parse_url( $url );
			$replace_target = $parsed_url['host'];
			if ( isset( $parsed_url['port'] ) && $parsed_url['port'] ) {
				$replace_target .= ":{$parsed_url['port']}";
			}
			$shared_attributes['permalink'] = preg_replace( "#{$replace_target}#i", $replaced_domain, $url );
		}
		return $shared_attributes;
	}


}
