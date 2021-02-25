#!/usr/bin/ruby

# By rodos@haywood.org
# Extract data from local Envoy and send to STDOUT in the format for the BitBar tool for Mac. 
# see https://github.com/matryer/bitbar

# <bitbar.title>Enphase Solar Status for Envoy</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Rodos</bitbar.author>
# <bitbar.author.github>iamrodos</bitbar.author.github>
# <bitbar.desc>Display the status of your Enphase Envoy solar system by quering to Envoy on the local network.</bitbar.desc>
# <bitbar.dependencies>ruby</bitbar.dependencies>
# <bitbar.abouturl>http://url-to-about.com/</bitbar.abouturl>

require 'net/http'
require 'net/http/digest_auth'
require 'json'

ENVOY_IP = "enter your IP address here"
SYSTEM_SIZE_WATTS = 6000 # Be good to derive this from the system but can't find it in local data, only via the Enlighten API

# If the number is great than 1000 shorten it to a k value
def shortNumberFormat(val)
    if val.abs < 1000
        return val.round(0).abs.to_s
    else
        return (val.abs/1000).round(1).to_s + "k"
    end
end

# Put comma separator into numbers
def separateComma(number)
    number.to_s.chars.to_a.reverse.each_slice(3).map(&:join).join(",").reverse
end

begin

    raise "Not a valid IP address. Update ENVOY_IP in script" unless ENVOY_IP.match(/^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/)

    http = Net::HTTP.new(ENVOY_IP)

    # Determine load values
    uri = URI("http://" + ENVOY_IP + "/production.json?details=1")
    req  = Net::HTTP::Get.new(uri.request_uri)
    req['Content-Type'] = 'application/json'
    res = http.request(req)
    raise "Error on http request. Response: " + res.message unless res.is_a?(Net::HTTPSuccess)
    importing = JSON.parse(res.body)["consumption"][1]["wNow"]
    consuming = JSON.parse(res.body)["consumption"][0]["wNow"]
    producing = JSON.parse(res.body)["production"][1]["wNow"]

    # Set the appropraite icon based on the power. Power plug, or shade or sun depending on grid load
    case 
    when importing > 0
        icon = "🔌" # Power plug
    when producing < (SYSTEM_SIZE_WATTS / 2)
        icon = "⛅" # Cloudy
    else
        icon = "☀️" # Sun
    end

    # Send out the first portion of the data for BitBar to display
    puts "#{icon} #{shortNumberFormat(importing)}W| color=#{importing > 0 ? "red":"green"} size=12"
    puts "---"
    puts "Producing #{separateComma(producing.round(0))}W|size=12"
    puts "Consuming #{separateComma(consuming.round(0))}W|size=12"

    # Get the serial number of the envoy
    uri = URI("http://" + ENVOY_IP + "/info.xml")
    req  = Net::HTTP::Get.new(uri.request_uri)
    res = http.request(req)
    raise "Error on http request. Response: " + res.message unless res.is_a?(Net::HTTPSuccess)

    # Hack out the <sn>...</sn> from the front of the XML returned. Not fancy.
    serial_number = res.body.scan(/sn>(\d*)<\/sn>/).first.first

    # Now lets see how much the panels are producing. This is an authenitcated request based on the serial number
    uri = URI('http://' + ENVOY_IP + '/api/v1/production/inverters')
    uri.user = 'envoy'
    uri.password = serial_number[-6,6]

    # Make the first request to get the auth
    req = Net::HTTP::Get.new uri.request_uri
    res = http.request(req)

    # Now send with an authentication digest
    digest_auth = Net::HTTP::DigestAuth.new
    auth = digest_auth.auth_header(uri, res['www-authenticate'], 'GET')
    req = Net::HTTP::Get.new(uri.request_uri)
    req.add_field('Authorization', auth)
    res = http.request(req)
    raise "Error on http request. Response: " + res.message unless res.is_a?(Net::HTTPSuccess)

    # Determine the range of invert output
    min = 99999999
    max = 0
    count = 0
    inverters = JSON.parse(res.body)
    inverters.each do |inverter|
        val = inverter["lastReportWatts"]
        next if val < 2
        count += 1
        min = val if val < min
        max = val if val > max
    end

    # Send out the inverter results for BitBar to display
    if count > 0
        puts "#{inverters.length} from #{min}W to #{max}W| size=12"
    else
        puts "No inverters generating.| size=12"
    end
    
rescue StandardError => e
    puts ":warning: Error| size=12"
    puts "---"
    puts e.message
end
